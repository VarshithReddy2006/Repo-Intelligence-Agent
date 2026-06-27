"""Function Call Graph Service.

Builds a function-to-function directed graph from a repository's Tree-sitter
AST and Symbol Index, then exposes algorithms for callers, callees, blast
radius, hierarchy, SCCs, and fan-in/fan-out analysis.

Design principles:
  - Reuses SymbolService for definition lookup (no re-parsing definitions).
  - Reuses TreeSitterService._get_parser() for call-site extraction.
  - Reuses GraphService.save_graph() / load_graph() for persistence.
  - Node IDs: "{file_path}::{qualified_name}"  (no collisions across files).
  - Disambiguation: same-file > same-dir > global; ties marked ambiguous=True.
  - Fabricated edges are never emitted. Prefer missing over incorrect.
  - Zero LLM calls. All computation is deterministic.

Persistence:
  - Graph pickle:  data/graphs/{owner}_{repo}_call_graph.pkl
  - Summary JSON:  data/call_graphs/{owner}_{repo}.json
"""

from __future__ import annotations

import logging
import os
import time
from collections import defaultdict
from datetime import datetime, timezone
from typing import Any, Dict, Generator, List, Optional, Set, Tuple

from core.repository_context import RepositoryContext
from storage.snapshot_store import SnapshotStore
from core.cache import AnalysisCache

import networkx as nx

from models.call_graph import (
    BlastRadiusResult,
    CallGraphSummary,
    CallHierarchyNode,
    CallNode,
)
from models.symbol import Symbol
from services.graph_service import GraphService
from services.symbol_service import SymbolService
from services.tree_sitter_service import TreeSitterService, _LANGUAGE_REGISTRY

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Storage
# ---------------------------------------------------------------------------
_CALL_GRAPHS_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "data",
    "call_graphs",
)
_SCHEMA_VERSION = 1

# Risk thresholds for blast radius
_BLAST_HIGH = 20
_BLAST_MED = 5

# Max BFS depth for hierarchy / blast radius
_MAX_HIERARCHY_DEPTH = 8
_MAX_BLAST_DEPTH = 10


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _node_id(file_path: str, qualified: str) -> str:
    """Build a globally unique node ID."""
    return f"{file_path}::{qualified}"


def _qualified(symbol: Symbol) -> str:
    """Build the dot-qualified name from a Symbol."""
    if symbol.parent_class:
        return f"{symbol.parent_class}.{symbol.name}"
    return symbol.name


def _file_dir(file_path: str) -> str:
    """Return the directory portion of a normalised path."""
    return "/".join(file_path.replace("\\", "/").split("/")[:-1])


class CallGraphService:
    """Builds and queries the function-level call graph.

    Injected as a singleton into the FastAPI app alongside the existing
    service singletons (graph_service, symbol_service, etc.).
    """

    @property
    def schema_version(self) -> int:
        return _SCHEMA_VERSION

    @classmethod
    def get_schema_version(cls) -> int:
        return _SCHEMA_VERSION

    def __init__(
        self,
        symbol_service: Optional[SymbolService] = None,
        graph_service: Optional[GraphService] = None,
        call_graphs_dir: str = _CALL_GRAPHS_DIR,
        snapshot_store: Optional[SnapshotStore] = None,
        analysis_cache: Optional[AnalysisCache] = None,
    ) -> None:
        self.symbol_service = symbol_service or SymbolService()
        self.graph_service = graph_service or GraphService()
        self.call_graphs_dir = call_graphs_dir
        os.makedirs(self.call_graphs_dir, exist_ok=True)

        if snapshot_store is None:
            if call_graphs_dir != _CALL_GRAPHS_DIR:
                parent_dir = os.path.dirname(call_graphs_dir)
                dir_name = os.path.basename(call_graphs_dir)
                from storage.snapshot_store import JsonSnapshotStore

                self.snapshot_store = JsonSnapshotStore(
                    base_dir=parent_dir, key_map={"call_graphs": dir_name}
                )
            else:
                from backend.dependencies import snapshot_store as default_store

                self.snapshot_store = default_store
        else:
            self.snapshot_store = snapshot_store

        self.analysis_cache = analysis_cache or AnalysisCache()

        self._ts = TreeSitterService()

    # ------------------------------------------------------------------
    # Public build API
    # ------------------------------------------------------------------

    def build(
        self,
        repo_name: str,
        files: Optional[List[Dict[str, str]]] = None,
        context: Optional[RepositoryContext] = None,
    ) -> Generator[Dict[str, Any], None, CallGraphSummary]:
        """Build the call graph. Yields SSE-style progress events.

        Provides backward compatibility by delegating to build_full.
        """
        return (yield from self.build_full(repo_name, context=context, files=files))

    def build_full(
        self,
        repo_name: str,
        context: Optional[RepositoryContext] = None,
        files: Optional[List[Dict[str, str]]] = None,
    ) -> Generator[Dict[str, Any], None, CallGraphSummary]:
        """Build the call graph from scratch."""
        yield {"status": "loading_symbols", "message": "Loading symbol index…"}

        if context is not None:
            symbol_index = context.symbol_index
        else:
            symbol_index = self.symbol_service.load(repo_name)

        if symbol_index is None:
            raise ValueError(
                f"No symbol index found for '{repo_name}'. "
                "Run POST /api/architecture/build first."
            )

        if files is None:
            if context and context.repo_path:
                files = self.symbol_service._walk_repo(context.repo_path)
            else:
                files = []

        yield {
            "status": "building_lookup",
            "message": "Building definition lookup table…",
        }

        # Build: name → list[Symbol] for fast callee resolution
        defn_by_name: Dict[str, List[Symbol]] = defaultdict(list)
        for sym in symbol_index.symbols:
            if sym.type in ("function", "method", "class"):
                defn_by_name[sym.name].append(sym)

        yield {
            "status": "extracting_calls",
            "message": f"Extracting call sites from {len(files)} files…",
        }

        # Collect all call edges across the repo
        all_nodes: Dict[str, CallNode] = {}

        # Register all known symbols as nodes first
        for sym in symbol_index.symbols:
            if sym.type in ("function", "method"):
                q = _qualified(sym)
                nid = _node_id(sym.file_path, q)
                if nid not in all_nodes:
                    all_nodes[nid] = CallNode(
                        node_id=nid,
                        name=sym.name,
                        qualified=q,
                        file_path=sym.file_path,
                        line_number=sym.line_number,
                        language=sym.language,
                        symbol_type=sym.type,
                        parent_class=sym.parent_class,
                    )

        # Extract call sites per file
        file_edges_map = {}
        for f in files:
            path = f.get("path", "")
            content = f.get("content", "")
            if not path or not content:
                continue
            file_edges = self._extract_call_edges(
                path, content, defn_by_name, all_nodes
            )
            file_edges_map[path] = file_edges

        # Cache call edges map
        self.snapshot_store.save(
            repo_name, "call_edges", {"edges": file_edges_map, "_schema_version": 1}
        )

        # Combine edges
        all_edges = []
        for edges in file_edges_map.values():
            all_edges.extend(edges)

        yield {
            "status": "building_graph",
            "message": f"Building graph ({len(all_nodes)} nodes, {len(all_edges)} edges)…",
        }

        # Build NetworkX DiGraph
        G: nx.DiGraph = nx.DiGraph()

        for nid, node in all_nodes.items():
            G.add_node(
                nid,
                name=node.name,
                qualified=node.qualified,
                file_path=node.file_path,
                line_number=node.line_number,
                language=node.language,
                symbol_type=node.symbol_type,
                parent_class=node.parent_class or "",
            )

        for caller_id, callee_id, call_line, ambiguous in all_edges:
            if caller_id in G and callee_id in G:
                # If edge exists, keep lowest call_line
                if G.has_edge(caller_id, callee_id):
                    existing = G[caller_id][callee_id]
                    if call_line < existing.get("call_line", call_line):
                        G[caller_id][callee_id]["call_line"] = call_line
                else:
                    G.add_edge(
                        caller_id,
                        callee_id,
                        call_line=call_line,
                        ambiguous=ambiguous,
                        relationship="calls",
                    )

        yield {"status": "computing_metrics", "message": "Computing graph metrics…"}

        # Annotate nodes with fan-in / fan-out / recursion
        recursive_ids: List[str] = []
        entry_ids: List[str] = []

        for nid in list(G.nodes()):
            fi = G.in_degree(nid)
            fo = G.out_degree(nid)
            is_recursive = G.has_edge(nid, nid)
            is_entry = fi == 0

            G.nodes[nid]["fan_in"] = fi
            G.nodes[nid]["fan_out"] = fo
            G.nodes[nid]["is_recursive"] = is_recursive
            G.nodes[nid]["is_entry"] = is_entry

            if is_recursive:
                recursive_ids.append(nid)
            if is_entry:
                entry_ids.append(nid)

        yield {"status": "persisting", "message": "Saving call graph…"}

        # Save graph via GraphService (reuses existing pickle mechanism)
        self.graph_service.save_graph(G, f"{repo_name}_call_graph")
        self.analysis_cache.set(repo_name, "graphs", G, 1, subkey="call")

        # Build and save summary
        top_fan_in = sorted(
            [{"node_id": n, "fan_in": G.in_degree(n)} for n in G.nodes()],
            key=lambda x: x["fan_in"],
            reverse=True,
        )[:10]
        top_fan_out = sorted(
            [{"node_id": n, "fan_out": G.out_degree(n)} for n in G.nodes()],
            key=lambda x: x["fan_out"],
            reverse=True,
        )[:10]

        summary = CallGraphSummary(
            repo=repo_name,
            generated_at=datetime.now(timezone.utc).isoformat(),
            node_count=G.number_of_nodes(),
            edge_count=G.number_of_edges(),
            entry_functions=entry_ids[:50],
            recursive_functions=recursive_ids,
            top_fan_in=top_fan_in,
            top_fan_out=top_fan_out,
        )
        self._save_summary(repo_name, summary)

        yield {
            "status": "complete",
            "message": f"✓ Call graph built: {G.number_of_nodes()} functions, {G.number_of_edges()} calls",
        }

        return summary

    def build_partial(
        self,
        repo_name: str,
        changed_files: Set[str],
        context: Optional[RepositoryContext] = None,
        files: Optional[List[Dict[str, str]]] = None,
    ) -> Generator[Dict[str, Any], None, CallGraphSummary]:
        """Incrementally update call edges and rebuild the call graph."""
        old_edges_data = self.snapshot_store.load(repo_name, "call_edges")
        if old_edges_data is None:
            logger.info(
                "No existing call edges cache found for %s, running full build.",
                repo_name,
            )
            return (yield from self.build_full(repo_name, context=context, files=files))

        yield {"status": "loading_symbols", "message": "Loading symbol index…"}

        if context is not None:
            symbol_index = context.symbol_index
        else:
            symbol_index = self.symbol_service.load(repo_name)

        if symbol_index is None:
            raise ValueError(
                f"No symbol index found for '{repo_name}'. "
                "Run POST /api/architecture/build first."
            )

        if files is None:
            if context and context.repo_path:
                files = self.symbol_service._walk_repo(context.repo_path)
            else:
                files = []

        yield {
            "status": "building_lookup",
            "message": "Building definition lookup table…",
        }

        # Build: name → list[Symbol] for fast callee resolution
        defn_by_name: Dict[str, List[Symbol]] = defaultdict(list)
        for sym in symbol_index.symbols:
            if sym.type in ("function", "method", "class"):
                defn_by_name[sym.name].append(sym)

        yield {
            "status": "extracting_calls",
            "message": "Extracting call sites from changed files…",
        }

        # Collect all call edges across the repo
        all_nodes: Dict[str, CallNode] = {}

        # Register all known symbols as nodes first
        for sym in symbol_index.symbols:
            if sym.type in ("function", "method"):
                q = _qualified(sym)
                nid = _node_id(sym.file_path, q)
                if nid not in all_nodes:
                    all_nodes[nid] = CallNode(
                        node_id=nid,
                        name=sym.name,
                        qualified=q,
                        file_path=sym.file_path,
                        line_number=sym.line_number,
                        language=sym.language,
                        symbol_type=sym.type,
                        parent_class=sym.parent_class,
                    )

        # 1. Filter out old call edges belonging to modified/deleted files
        file_edges_map = old_edges_data.get("edges", {})
        for path in list(file_edges_map.keys()):
            if path in changed_files:
                del file_edges_map[path]

        # 2. Extract new call edges for added/modified files
        for f in files:
            path = f.get("path", "")
            if path in changed_files:
                content = f.get("content", "")
                if path and content:
                    file_edges = self._extract_call_edges(
                        path, content, defn_by_name, all_nodes
                    )
                    file_edges_map[path] = file_edges

        if files is None or not any(f.get("path") in changed_files for f in files):
            repo_path = context.repo_path if context else None
            if repo_path:
                for path in changed_files:
                    full_path = os.path.join(repo_path, path)
                    if os.path.exists(full_path):
                        try:
                            with open(
                                full_path, "r", encoding="utf-8", errors="ignore"
                            ) as fh:
                                content = fh.read()
                            file_edges = self._extract_call_edges(
                                path, content, defn_by_name, all_nodes
                            )
                            file_edges_map[path] = file_edges
                        except Exception:
                            pass

        # 3. Save updated edges map
        self.snapshot_store.save(
            repo_name, "call_edges", {"edges": file_edges_map, "_schema_version": 1}
        )

        # 4. Combine all edges
        all_edges = []
        for edges in file_edges_map.values():
            all_edges.extend(edges)

        yield {
            "status": "building_graph",
            "message": f"Building graph ({len(all_nodes)} nodes, {len(all_edges)} edges)…",
        }

        # Build NetworkX DiGraph
        G: nx.DiGraph = nx.DiGraph()

        for nid, node in all_nodes.items():
            G.add_node(
                nid,
                name=node.name,
                qualified=node.qualified,
                file_path=node.file_path,
                line_number=node.line_number,
                language=node.language,
                symbol_type=node.symbol_type,
                parent_class=node.parent_class or "",
            )

        for caller_id, callee_id, call_line, ambiguous in all_edges:
            if caller_id in G and callee_id in G:
                if G.has_edge(caller_id, callee_id):
                    existing = G[caller_id][callee_id]
                    if call_line < existing.get("call_line", call_line):
                        G[caller_id][callee_id]["call_line"] = call_line
                else:
                    G.add_edge(
                        caller_id,
                        callee_id,
                        call_line=call_line,
                        ambiguous=ambiguous,
                        relationship="calls",
                    )

        yield {"status": "computing_metrics", "message": "Computing graph metrics…"}

        # Annotate nodes with fan-in / fan-out / recursion
        recursive_ids: List[str] = []
        entry_ids: List[str] = []

        for nid in list(G.nodes()):
            fi = G.in_degree(nid)
            fo = G.out_degree(nid)
            is_recursive = G.has_edge(nid, nid)
            is_entry = fi == 0

            G.nodes[nid]["fan_in"] = fi
            G.nodes[nid]["fan_out"] = fo
            G.nodes[nid]["is_recursive"] = is_recursive
            G.nodes[nid]["is_entry"] = is_entry

            if is_recursive:
                recursive_ids.append(nid)
            if is_entry:
                entry_ids.append(nid)

        # Re-save graph
        self.graph_service.save_graph(G, f"{repo_name}_call_graph")
        self.analysis_cache.set(repo_name, "graphs", G, 1, subkey="call")

        # Build and save summary
        top_fan_in = sorted(
            [{"node_id": n, "fan_in": G.in_degree(n)} for n in G.nodes()],
            key=lambda x: x["fan_in"],
            reverse=True,
        )[:10]
        top_fan_out = sorted(
            [{"node_id": n, "fan_out": G.out_degree(n)} for n in G.nodes()],
            key=lambda x: x["fan_out"],
            reverse=True,
        )[:10]

        # Aggregate summary metrics
        summary = CallGraphSummary(
            repo=repo_name,
            generated_at=datetime.now(timezone.utc).isoformat(),
            node_count=G.number_of_nodes(),
            edge_count=G.number_of_edges(),
            entry_functions=entry_ids[:50],
            recursive_functions=recursive_ids,
            top_fan_in=top_fan_in,
            top_fan_out=top_fan_out,
        )
        self._save_summary(repo_name, summary)

        yield {
            "status": "complete",
            "message": f"✓ Call graph built: {G.number_of_nodes()} functions, {G.number_of_edges()} calls",
        }

        return summary

    # ------------------------------------------------------------------
    # Public query API
    # ------------------------------------------------------------------

    def graph_exists(self, repo_name: str) -> bool:
        """Return True if a call graph pickle exists."""
        return self.graph_service.graph_exists(f"{repo_name}_call_graph")

    def load_graph(self, repo_name: str) -> Optional[nx.DiGraph]:
        """Load the call graph from disk."""
        cached = self.analysis_cache.get(repo_name, "graphs", 1, subkey="call")
        if cached is not None:
            return cached

        graph = self.graph_service.load_graph(f"{repo_name}_call_graph")
        if graph is not None:
            self.analysis_cache.set(repo_name, "graphs", graph, 1, subkey="call")
        return graph

    def load_summary(self, repo_name: str) -> Optional[CallGraphSummary]:
        """Load the persisted call graph summary."""
        cached = self.analysis_cache.get(repo_name, "call_graph", _SCHEMA_VERSION)
        if cached is not None:
            return cached

        data = self._load_raw_summary(repo_name)
        if data is None:
            return None

        stored_ver = data.get("_schema_version", 0)
        if stored_ver < _SCHEMA_VERSION:
            logger.warning(
                "Discarding stale call graph summary for %s (v%d < v%d)",
                repo_name,
                stored_ver,
                _SCHEMA_VERSION,
            )
            return None

        try:
            filtered = {k: v for k, v in data.items() if not k.startswith("_")}
            summary = CallGraphSummary(**filtered)
            self.analysis_cache.set(repo_name, "call_graph", summary, _SCHEMA_VERSION)
            return summary
        except Exception as exc:
            logger.error("Failed to deserialise call graph summary: %s", exc)
            return None

    def get_node(self, repo_name: str, function_id: str) -> Optional[CallNode]:
        """Return metadata for a single function node."""
        G = self.load_graph(repo_name)
        if G is None or function_id not in G:
            return None
        return self._node_from_graph(G, function_id)

    def get_callers(self, repo_name: str, function_id: str) -> List[CallNode]:
        """Return all functions that directly call *function_id*."""
        G = self.load_graph(repo_name)
        if G is None or function_id not in G:
            return []
        return [self._node_from_graph(G, n) for n in G.predecessors(function_id)]

    def get_callees(self, repo_name: str, function_id: str) -> List[CallNode]:
        """Return all functions directly called by *function_id*."""
        G = self.load_graph(repo_name)
        if G is None or function_id not in G:
            return []
        return [self._node_from_graph(G, n) for n in G.successors(function_id)]

    def get_blast_radius(self, repo_name: str, function_id: str) -> BlastRadiusResult:
        """Compute function-level blast radius via BFS on callers.

        'Who would be affected if I changed this function?' — walks backward
        through the call graph to find all functions that transitively call
        function_id, up to _MAX_BLAST_DEPTH hops.
        """
        G = self.load_graph(repo_name)
        if G is None or function_id not in G:
            return BlastRadiusResult(
                function_id=function_id,
                risk_level="low",
            )

        # BFS on reversed graph (callers of callers)
        affected: Set[str] = set()
        queue = [(function_id, 0)]
        max_depth_reached = 0

        while queue:
            node, depth = queue.pop(0)
            if depth >= _MAX_BLAST_DEPTH:
                continue
            for caller in G.predecessors(node):
                if caller not in affected and caller != function_id:
                    affected.add(caller)
                    max_depth_reached = max(max_depth_reached, depth + 1)
                    queue.append((caller, depth + 1))

        affected_list = sorted(affected)
        affected_files = sorted(
            {
                G.nodes[n].get("file_path", "")
                for n in affected_list
                if G.nodes[n].get("file_path")
            }
        )

        n = len(affected_list)
        risk = "high" if n >= _BLAST_HIGH else "medium" if n >= _BLAST_MED else "low"

        # Detect SCCs (mutual recursion / cycles) in the affected subgraph
        subgraph = G.subgraph(set(affected_list) | {function_id})
        sccs = [
            list(c) for c in nx.strongly_connected_components(subgraph) if len(c) > 1
        ]

        return BlastRadiusResult(
            function_id=function_id,
            affected_functions=affected_list,
            affected_files=affected_files,
            depth=max_depth_reached,
            risk_level=risk,
            recursive_cycles=sccs,
        )

    def get_hierarchy(
        self,
        repo_name: str,
        function_id: str,
        direction: str = "down",
        max_depth: int = _MAX_HIERARCHY_DEPTH,
    ) -> Optional[CallHierarchyNode]:
        """Build a call hierarchy tree rooted at *function_id*.

        direction="down": show what this function calls (callees).
        direction="up":   show what calls this function (callers).
        """
        G = self.load_graph(repo_name)
        if G is None or function_id not in G:
            return None

        visited: Set[str] = set()

        def build_tree(node_id: str, depth: int) -> CallHierarchyNode:
            attrs = G.nodes.get(node_id, {})
            is_back_edge = node_id in visited and depth > 0
            visited.add(node_id)

            children: List[CallHierarchyNode] = []
            if depth < max_depth and not is_back_edge:
                neighbours = (
                    list(G.successors(node_id))
                    if direction == "down"
                    else list(G.predecessors(node_id))
                )
                for nb in neighbours:
                    children.append(build_tree(nb, depth + 1))

            return CallHierarchyNode(
                node_id=node_id,
                name=attrs.get("name", node_id),
                qualified=attrs.get("qualified", node_id),
                file_path=attrs.get("file_path", ""),
                children=children,
                depth=depth,
                is_recursive_back_edge=is_back_edge,
            )

        return build_tree(function_id, 0)

    def get_stats(self, repo_name: str) -> Dict[str, Any]:
        """Return aggregate call graph statistics."""
        G = self.load_graph(repo_name)
        summary = self.load_summary(repo_name)

        if G is None:
            return {"error": "Call graph not found. Run build first."}

        sccs = list(nx.strongly_connected_components(G))
        non_trivial_sccs = [c for c in sccs if len(c) > 1]

        return {
            "node_count": G.number_of_nodes(),
            "edge_count": G.number_of_edges(),
            "entry_functions": len([n for n in G.nodes() if G.in_degree(n) == 0]),
            "recursive_functions": len([n for n in G.nodes() if G.has_edge(n, n)]),
            "mutual_recursion_groups": len(non_trivial_sccs),
            "top_fan_in": summary.top_fan_in if summary else [],
            "top_fan_out": summary.top_fan_out if summary else [],
            "generated_at": summary.generated_at if summary else None,
        }

    def get_unreachable_functions(
        self, repo_name: str, entry_function_ids: Optional[List[str]] = None
    ) -> List[str]:
        """Return function IDs unreachable from entry points.

        Used by Dead Code Detection to surface unreachable functions
        (not just unreachable files).
        """
        G = self.load_graph(repo_name)
        if G is None:
            return []

        # Use provided entry points or auto-detect (nodes with no callers)
        entries = set(entry_function_ids or [])
        if not entries:
            entries = {n for n in G.nodes() if G.in_degree(n) == 0}

        reachable: Set[str] = set(entries)
        for ep in entries:
            if ep in G:
                reachable.update(nx.descendants(G, ep))

        return sorted(set(G.nodes()) - reachable)

    def search_functions(
        self, repo_name: str, query: str, limit: int = 20
    ) -> List[CallNode]:
        """Search for functions by name substring."""
        G = self.load_graph(repo_name)
        if G is None:
            return []
        q = query.lower()
        matches = []
        for nid in G.nodes():
            attrs = G.nodes[nid]
            name = attrs.get("name", "").lower()
            qualified = attrs.get("qualified", "").lower()
            if q in name or q in qualified or q in nid.lower():
                matches.append(self._node_from_graph(G, nid))
        return matches[:limit]

    # ------------------------------------------------------------------
    # React Flow serialisation
    # ------------------------------------------------------------------

    def get_graph_json(
        self,
        repo_name: str,
        search_query: Optional[str] = None,
        max_nodes: int = 300,
        max_edges: int = 1000,
    ) -> Dict[str, Any]:
        """Return the call graph as React Flow-compatible JSON.

        Mirrors GraphSerializer._serialise() schema so the frontend
        InteractiveDependencyGraph component can render it unchanged.
        """
        G = self.load_graph(repo_name)
        if G is None:
            return {
                "nodes": [],
                "edges": [],
                "node_count": 0,
                "edge_count": 0,
                "error": "Call graph not found. Run build first.",
            }

        # Filter by search query if provided
        if search_query and search_query.strip():
            q = search_query.lower()
            matching = {
                n
                for n in G.nodes()
                if q in G.nodes[n].get("name", "").lower()
                or q in G.nodes[n].get("qualified", "").lower()
                or q in G.nodes[n].get("file_path", "").lower()
            }
            context = set(matching)
            for m in matching:
                context.update(G.predecessors(m))
                context.update(G.successors(m))
            working = G.subgraph(context)
        else:
            # Priority sort: high fan-in first (most-called = most important)
            sorted_nodes = sorted(
                G.nodes(),
                key=lambda n: G.in_degree(n),
                reverse=True,
            )[:max_nodes]
            working = G.subgraph(sorted_nodes)

        centrality: Dict[str, float] = {}
        if working.number_of_nodes() > 1:
            try:
                centrality = nx.degree_centrality(working)
            except Exception:
                centrality = {}

        res_nodes = []
        for n in working.nodes():
            attrs = working.nodes[n]
            fi = working.in_degree(n)
            fo = working.out_degree(n)
            cat = (
                "entry_point" if fi == 0 else ("core_module" if fi >= 5 else "regular")
            )
            if attrs.get("is_recursive"):
                cat = "high_coupling"

            res_nodes.append(
                {
                    "id": n,
                    "label": attrs.get("name", n),
                    "category": cat,
                    "degree": fi + fo,
                    "centrality": round(centrality.get(n, 0.0), 4),
                    "language": attrs.get("language", "unknown"),
                    "highlighted": False,
                    "is_focus": False,
                    # Call-graph-specific extras
                    "qualified": attrs.get("qualified", ""),
                    "file_path": attrs.get("file_path", ""),
                    "fan_in": fi,
                    "fan_out": fo,
                    "is_recursive": attrs.get("is_recursive", False),
                    "parent_class": attrs.get("parent_class", ""),
                    "symbol_type": attrs.get("symbol_type", "function"),
                }
            )

        res_edges = []
        count = 0
        for u, v, eattrs in working.edges(data=True):
            if count >= max_edges:
                break
            res_edges.append(
                {
                    "source": u,
                    "target": v,
                    "relationship": "calls",
                    "ambiguous": eattrs.get("ambiguous", False),
                }
            )
            count += 1

        return {
            "nodes": res_nodes,
            "edges": res_edges,
            "node_count": working.number_of_nodes(),
            "edge_count": working.number_of_edges(),
        }

    def get_neighbors_json(self, repo_name: str, function_id: str) -> Dict[str, Any]:
        """Return immediate callers + callees as React Flow JSON."""
        G = self.load_graph(repo_name)
        if G is None or function_id not in G:
            return {
                "nodes": [],
                "edges": [],
                "node_count": 0,
                "edge_count": 0,
                "error": f"Function '{function_id}' not found.",
            }

        context = {function_id}
        context.update(G.predecessors(function_id))
        context.update(G.successors(function_id))
        return self._serialise_subgraph(G, context, focus_id=function_id)

    def get_trace_json(
        self,
        repo_name: str,
        function_id: str,
        direction: str = "both",
        depth: int = 6,
    ) -> Dict[str, Any]:
        """Return BFS trace from *function_id* as React Flow JSON."""
        G = self.load_graph(repo_name)
        if G is None or function_id not in G:
            return {
                "nodes": [],
                "edges": [],
                "node_count": 0,
                "edge_count": 0,
                "error": f"Function '{function_id}' not found.",
            }

        reachable: Set[str] = {function_id}
        highlighted: Set[str] = set()

        if direction in ("forward", "both"):
            fwd = self._bfs(G, function_id, forward=True, max_depth=depth)
            reachable.update(fwd)
            highlighted.update(fwd)

        if direction in ("backward", "both"):
            bwd = self._bfs(G, function_id, forward=False, max_depth=depth)
            reachable.update(bwd)
            highlighted.update(bwd)

        return self._serialise_subgraph(
            G, reachable, focus_id=function_id, highlighted=highlighted
        )

    # ------------------------------------------------------------------
    # AST call-site extraction
    # ------------------------------------------------------------------

    def _extract_call_edges(
        self,
        file_path: str,
        content: str,
        defn_by_name: Dict[str, List[Symbol]],
        all_nodes: Dict[str, "CallNode"],
    ) -> List[Tuple[str, str, int, bool]]:
        """Walk the AST and extract call edges for all functions in *file_path*.

        Returns list of (caller_id, callee_id, call_line, ambiguous) tuples.
        Only emits edges where both caller and callee nodes already exist in
        all_nodes (no fabricated nodes).
        """
        ext = os.path.splitext(file_path)[1].lower()
        if ext not in _LANGUAGE_REGISTRY:
            return []

        language_name, loader = _LANGUAGE_REGISTRY[ext]
        parser = self._ts._get_parser(language_name, loader)
        if parser is None:
            return []

        try:
            tree = parser.parse(content.encode("utf-8", errors="replace"))
        except Exception as exc:
            logger.debug("Call extraction parse error for %s: %s", file_path, exc)
            return []

        # Build file-local function scope stack:
        # maps (start_byte, end_byte) → caller_node_id
        scopes = self._build_scope_map(
            tree.root_node, file_path, all_nodes, language_name
        )

        # Extract all call expressions from the AST
        call_sites = self._find_call_sites(tree.root_node, language_name)

        edges: List[Tuple[str, str, int, bool]] = []
        for call_name, call_line, call_byte in call_sites:
            # Find the enclosing function scope
            caller_id = self._find_enclosing_scope(call_byte, scopes)
            if caller_id is None:
                continue  # call outside any tracked function

            # Resolve callee
            callee_id, ambiguous = self._resolve_callee(
                call_name, caller_id, file_path, defn_by_name, all_nodes
            )
            if callee_id is None:
                continue  # unresolved (external library or dynamic call)

            if caller_id == callee_id:
                # Direct recursion — always certain
                edges.append((caller_id, callee_id, call_line, False))
            else:
                edges.append((caller_id, callee_id, call_line, ambiguous))

        return edges

    def _build_scope_map(
        self,
        root,
        file_path: str,
        all_nodes: Dict[str, "CallNode"],
        language_name: str,
    ) -> List[Tuple[int, int, str]]:
        """Build a list of (start_byte, end_byte, node_id) for all tracked functions."""
        scopes: List[Tuple[int, int, str]] = []

        def walk(node, parent_class: Optional[str] = None):
            nt = node.type

            if language_name == "python":
                if nt == "class_definition":
                    class_name = self._get_first_identifier(node)
                    for child in node.children:
                        walk(child, parent_class=class_name)
                    return
                if nt in ("function_definition", "decorated_definition"):
                    actual = node
                    if nt == "decorated_definition":
                        actual = next(
                            (
                                c
                                for c in node.children
                                if c.type == "function_definition"
                            ),
                            None,
                        )
                    if actual is None:
                        return
                    fn_name = self._get_first_identifier(actual)
                    if fn_name:
                        q = f"{parent_class}.{fn_name}" if parent_class else fn_name
                        nid = _node_id(file_path, q)
                        if nid in all_nodes:
                            scopes.append((actual.start_byte, actual.end_byte, nid))
                    for child in actual.children:
                        walk(child, parent_class=parent_class)
                    return

            else:  # JS/TS
                if nt in ("class_declaration", "class"):
                    class_name = self._get_first_identifier(node)
                    for child in node.children:
                        walk(child, parent_class=class_name)
                    return
                if nt == "method_definition":
                    fn_name = self._get_first_identifier(node)
                    if fn_name and parent_class:
                        q = f"{parent_class}.{fn_name}"
                        nid = _node_id(file_path, q)
                        if nid in all_nodes:
                            scopes.append((node.start_byte, node.end_byte, nid))
                    for child in node.children:
                        walk(child, parent_class=parent_class)
                    return
                if nt == "function_declaration":
                    fn_name = self._get_first_identifier(node)
                    if fn_name:
                        q = f"{parent_class}.{fn_name}" if parent_class else fn_name
                        nid = _node_id(file_path, q)
                        if nid in all_nodes:
                            scopes.append((node.start_byte, node.end_byte, nid))
                    for child in node.children:
                        walk(child, parent_class=parent_class)
                    return
                if nt == "export_statement":
                    for child in node.children:
                        walk(child, parent_class=parent_class)
                    return

            for child in node.children:
                walk(child, parent_class=parent_class)

        walk(root)
        return scopes

    def _find_call_sites(self, root, language_name: str) -> List[Tuple[str, int, int]]:
        """Walk AST and return all (callee_name, line_1indexed, start_byte) tuples."""
        results: List[Tuple[str, int, int]] = []

        def walk(node):
            nt = node.type
            if language_name == "python" and nt == "call":
                # Python: call → (attribute|identifier) + arguments
                fn_child = node.children[0] if node.children else None
                if fn_child:
                    if fn_child.type == "identifier":
                        name = fn_child.text.decode("utf-8", errors="replace")
                        results.append((name, node.start_point[0] + 1, node.start_byte))
                    elif fn_child.type == "attribute":
                        # obj.method(…) — extract method name only
                        for c in fn_child.children:
                            if c.type in ("identifier", "property_identifier"):
                                # Only take the last identifier (the method)
                                pass
                        children = fn_child.children
                        if children:
                            last = children[-1]
                            if last.type in ("identifier", "property_identifier"):
                                name = last.text.decode("utf-8", errors="replace")
                                results.append(
                                    (name, node.start_point[0] + 1, node.start_byte)
                                )

            elif language_name != "python" and nt == "call_expression":
                fn_child = node.children[0] if node.children else None
                if fn_child:
                    if fn_child.type == "identifier":
                        name = fn_child.text.decode("utf-8", errors="replace")
                        results.append((name, node.start_point[0] + 1, node.start_byte))
                    elif fn_child.type in ("member_expression",):
                        # obj.method(…)
                        for c in fn_child.children:
                            if c.type in ("property_identifier", "identifier"):
                                pass
                        children = fn_child.children
                        if children:
                            last = children[-1]
                            if last.type in ("property_identifier", "identifier"):
                                name = last.text.decode("utf-8", errors="replace")
                                results.append(
                                    (name, node.start_point[0] + 1, node.start_byte)
                                )

            for child in node.children:
                walk(child)

        walk(root)
        return results

    @staticmethod
    def _find_enclosing_scope(
        call_byte: int,
        scopes: List[Tuple[int, int, str]],
    ) -> Optional[str]:
        """Return the narrowest scope (smallest byte range) enclosing *call_byte*."""
        best_id: Optional[str] = None
        best_size = float("inf")
        for start, end, nid in scopes:
            if start <= call_byte <= end:
                size = end - start
                if size < best_size:
                    best_size = size
                    best_id = nid
        return best_id

    def _resolve_callee(
        self,
        call_name: str,
        caller_id: str,
        caller_file: str,
        defn_by_name: Dict[str, List[Symbol]],
        all_nodes: Dict[str, "CallNode"],
    ) -> Tuple[Optional[str], bool]:
        """Resolve a call_name to a node_id using scope-based disambiguation.

        Priority:
          1. Same file, exact name match
          2. Same directory, exact name match
          3. Any file, exact name match (possibly ambiguous)

        Returns (node_id, ambiguous). Never fabricates a node.
        """
        candidates = defn_by_name.get(call_name, [])
        if not candidates:
            return None, False

        caller_dir = _file_dir(caller_file)

        # Score each candidate
        same_file = [s for s in candidates if s.file_path == caller_file]
        same_dir = [
            s
            for s in candidates
            if _file_dir(s.file_path) == caller_dir and s.file_path != caller_file
        ]
        global_rest = [
            s
            for s in candidates
            if s.file_path != caller_file and _file_dir(s.file_path) != caller_dir
        ]

        def first_valid(syms: List[Symbol]) -> Tuple[Optional[str], bool]:
            valid = [
                s
                for s in syms
                if s.type in ("function", "method")
                and _node_id(s.file_path, _qualified(s)) in all_nodes
            ]
            if not valid:
                return None, False
            nid = _node_id(valid[0].file_path, _qualified(valid[0]))
            return nid, len(valid) > 1

        nid, amb = first_valid(same_file)
        if nid:
            return nid, amb

        nid, amb = first_valid(same_dir)
        if nid:
            return nid, amb

        nid, amb = first_valid(global_rest)
        if nid:
            return nid, len(
                global_rest
            ) > 1  # global match is always potentially ambiguous

        return None, False

    # ------------------------------------------------------------------
    # Shared serialisation helper
    # ------------------------------------------------------------------

    def _serialise_subgraph(
        self,
        G: nx.DiGraph,
        node_ids: Set[str],
        focus_id: Optional[str] = None,
        highlighted: Optional[Set[str]] = None,
        max_edges: int = 1000,
    ) -> Dict[str, Any]:
        """Serialise a node subset to React Flow JSON."""
        highlighted = highlighted or set()
        subgraph = G.subgraph(node_ids)

        centrality: Dict[str, float] = {}
        if subgraph.number_of_nodes() > 1:
            try:
                centrality = nx.degree_centrality(subgraph)
            except Exception:
                pass

        res_nodes = []
        for n in subgraph.nodes():
            attrs = subgraph.nodes[n]
            fi = subgraph.in_degree(n)
            fo = subgraph.out_degree(n)
            cat = (
                "focus"
                if n == focus_id
                else (
                    "entry_point"
                    if fi == 0
                    else "core_module"
                    if fi >= 5
                    else "regular"
                )
            )
            if attrs.get("is_recursive"):
                cat = "high_coupling" if n != focus_id else cat

            res_nodes.append(
                {
                    "id": n,
                    "label": attrs.get("name", n),
                    "category": cat,
                    "degree": fi + fo,
                    "centrality": round(centrality.get(n, 0.0), 4),
                    "language": attrs.get("language", "unknown"),
                    "highlighted": n in highlighted,
                    "is_focus": n == focus_id,
                    "qualified": attrs.get("qualified", ""),
                    "file_path": attrs.get("file_path", ""),
                    "fan_in": fi,
                    "fan_out": fo,
                    "is_recursive": attrs.get("is_recursive", False),
                    "parent_class": attrs.get("parent_class", ""),
                    "symbol_type": attrs.get("symbol_type", "function"),
                }
            )

        res_edges = []
        count = 0
        for u, v, eattrs in subgraph.edges(data=True):
            if count >= max_edges:
                break
            res_edges.append(
                {
                    "source": u,
                    "target": v,
                    "relationship": "calls",
                    "ambiguous": eattrs.get("ambiguous", False),
                }
            )
            count += 1

        return {
            "nodes": res_nodes,
            "edges": res_edges,
            "node_count": subgraph.number_of_nodes(),
            "edge_count": subgraph.number_of_edges(),
        }

    # ------------------------------------------------------------------
    # Static helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _get_first_identifier(node) -> str:
        for child in node.children:
            if child.type in ("identifier", "type_identifier", "property_identifier"):
                return child.text.decode("utf-8", errors="replace")
        return ""

    @staticmethod
    def _bfs(
        G: nx.DiGraph,
        start: str,
        forward: bool,
        max_depth: int,
    ) -> Set[str]:
        """Simple BFS returning visited nodes (excluding start)."""
        if start not in G:
            return set()
        visited: Set[str] = set()
        queue = [(start, 0)]
        while queue:
            node, depth = queue.pop(0)
            if depth >= max_depth:
                continue
            neighbours = (
                list(G.successors(node)) if forward else list(G.predecessors(node))
            )
            for nb in neighbours:
                if nb not in visited and nb != start:
                    visited.add(nb)
                    queue.append((nb, depth + 1))
        return visited

    @staticmethod
    def _node_from_graph(G: nx.DiGraph, node_id: str) -> CallNode:
        attrs = G.nodes.get(node_id, {})
        return CallNode(
            node_id=node_id,
            name=attrs.get("name", node_id),
            qualified=attrs.get("qualified", node_id),
            file_path=attrs.get("file_path", ""),
            line_number=attrs.get("line_number", 1),
            language=attrs.get("language", "unknown"),
            symbol_type=attrs.get("symbol_type", "function"),
            parent_class=attrs.get("parent_class") or None,
            is_entry=attrs.get("is_entry", False),
            is_recursive=attrs.get("is_recursive", False),
            fan_in=G.in_degree(node_id),
            fan_out=G.out_degree(node_id),
        )

    # ------------------------------------------------------------------
    # Persistence helpers
    # ------------------------------------------------------------------

    def _summary_path(self, repo_name: str) -> str:
        return self.snapshot_store._get_path(repo_name, "call_graphs")

    def _save_summary(self, repo_name: str, summary: CallGraphSummary) -> None:
        payload = summary.model_dump()
        payload["_schema_version"] = _SCHEMA_VERSION
        payload["_built_at"] = int(time.time())
        self.snapshot_store.save(repo_name, "call_graphs", payload)
        self.analysis_cache.set(repo_name, "call_graph", summary, _SCHEMA_VERSION)

    def _load_raw_summary(self, repo_name: str) -> Optional[Dict[str, Any]]:
        return self.snapshot_store.load(repo_name, "call_graphs")
