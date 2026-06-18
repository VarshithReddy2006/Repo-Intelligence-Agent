"""Architecture Service.

Orchestrates the full Architecture Intelligence pipeline:
  1. Parse repository files with TreeSitterService
  2. Detect entry points with EntryPointService
  3. Build dependency graphs with GraphService
  4. Compute architecture metadata locally (no LLM)
  5. Persist graph and summary to disk

All computations are local — no Gemini calls are made in this service.
"""

import json
import logging
import os
import time
from typing import Any, Dict, List, Optional

import networkx as nx

from services.tree_sitter_service import TreeSitterService
from services.graph_service import GraphService
from services.entry_point_service import EntryPointService
from models.architecture import ArchitectureSummary as ArchSummary

logger = logging.getLogger(__name__)

# Default storage directory relative to project root
_ARCH_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "data",
    "architecture",
)

# Increment this whenever the summary schema or computation logic changes.
# A persisted summary with a lower version is treated as stale and rebuilt
# automatically, preventing the "zero dependencies from an old empty run"
# class of bugs.
_SUMMARY_SCHEMA_VERSION = 2


class ArchitectureService:
    """Builds and persists the architecture intelligence layer for a repository.

    This service is stateless; each call to build() operates independently.
    Results are written to disk and can be retrieved without rebuilding.
    """

    def __init__(
        self,
        arch_dir: str = _ARCH_DIR,
        graphs_dir: Optional[str] = None,
    ) -> None:
        """Initialise the service.

        Args:
            arch_dir:   Directory where architecture JSON summaries are saved.
            graphs_dir: Directory where graph pickle files are saved.
                        Defaults to GraphService's default when None.
        """
        self.arch_dir = arch_dir
        os.makedirs(self.arch_dir, exist_ok=True)

        self.tree_sitter = TreeSitterService()
        self.graph_service = GraphService(**({"graphs_dir": graphs_dir} if graphs_dir else {}))
        self.entry_point_service = EntryPointService()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def build(
        self,
        repo_name: str,
        repo_path: Optional[str] = None,
        files: Optional[List[Dict[str, str]]] = None,
        force_rebuild: bool = False,
    ) -> Dict[str, Any]:
        """Run the full architecture build pipeline for a repository.

        Provide either *repo_path* (path to cloned directory on disk) or
        *files* (pre-extracted [{path, content}] list).  At least one must
        be given.

        Args:
            repo_name:      Repository identifier (owner/repo).
            repo_path:      Local path to the cloned repository.
            files:          Pre-extracted file list.
            force_rebuild:  If True, rebuild even if a persisted graph exists.

        Returns:
            A dictionary with:
                status            – "success"
                repo              – repo_name
                files_parsed      – number of files successfully parsed
                dependencies_found– total graph edges
                entry_points      – list of detected entry point paths
                architecture      – ArchitectureSummary dict
        """
        if repo_path is None and files is None:
            raise ValueError("Provide either repo_path or files.")

        logger.info("Starting architecture build for %s", repo_name)

        # ----------------------------------------------------------
        # Step 1: Parse files
        # ----------------------------------------------------------
        parsed = self.tree_sitter.parse_repository(
            repo_path=repo_path or "",
            files=files,
        )
        logger.info("Parsed %d supported source files", len(parsed))

        # ----------------------------------------------------------
        # Step 2: Detect entry points
        # ----------------------------------------------------------
        all_paths = (
            [f["path"] for f in files]
            if files
            else self._walk_repo_paths(repo_path)
        )
        ep_result = self.entry_point_service.detect(all_paths, parsed)
        entry_points: List[str] = ep_result["entry_points"]
        logger.info("Detected %d entry points: %s", len(entry_points), entry_points)

        # ----------------------------------------------------------
        # Step 3: Build file dependency graph
        # ----------------------------------------------------------
        graph = self.graph_service.build_file_graph(parsed)

        # ----------------------------------------------------------
        # Step 4: Compute architecture metrics (local, no LLM)
        # ----------------------------------------------------------
        summary = self._compute_summary(
            graph=graph,
            entry_points=entry_points,
            total_files=len(all_paths),
        )

        # ----------------------------------------------------------
        # Step 5: Persist
        # ----------------------------------------------------------
        self.graph_service.save_graph(graph, repo_name)
        self._save_summary(repo_name, summary)

        logger.info(
            "Architecture build complete for %s — %d files parsed, %d deps found",
            repo_name,
            len(parsed),
            graph.number_of_edges(),
        )

        return {
            "status": "success",
            "repo": repo_name,
            "files_parsed": len(parsed),
            "dependencies_found": graph.number_of_edges(),
            "entry_points": entry_points,
            "architecture": summary,
        }

    def get_summary(self, repo_name: str) -> Optional[ArchSummary]:
        """Load and return a persisted architecture summary.

        Args:
            repo_name: Repository identifier (owner/repo).

        Returns:
            An ArchitectureSummary Pydantic model, or None if not found.
        """
        data = self._load_summary(repo_name)
        if data is None:
            return None
        return ArchSummary(**data)

    def summary_exists(self, repo_name: str) -> bool:
        """Return True if a persisted architecture summary exists."""
        return os.path.exists(self._summary_path(repo_name))

    # ------------------------------------------------------------------
    # Architecture metric computation
    # ------------------------------------------------------------------

    @staticmethod
    def _compute_summary(
        graph: nx.DiGraph,
        entry_points: List[str],
        total_files: int,
        top_n: int = 10,
    ) -> Dict[str, Any]:
        """Compute architecture metrics purely from the graph.

        Uses NetworkX degree centrality to identify core modules and
        in/out-degree sums to identify high-coupling modules.

        Args:
            graph:       File dependency graph.
            entry_points: Detected entry point paths.
            total_files: Total number of files in the repository.
            top_n:       Number of top modules to return.

        Returns:
            Dict matching the ArchitectureSummary schema.
        """
        total_deps = graph.number_of_edges()

        if graph.number_of_nodes() == 0:
            return {
                "entry_points": entry_points,
                "core_modules": [],
                "high_coupling_modules": [],
                "total_files": total_files,
                "total_dependencies": total_deps,
            }

        # Degree centrality — identifies nodes that are most connected overall
        centrality = nx.degree_centrality(graph)
        sorted_by_centrality = sorted(centrality.items(), key=lambda x: x[1], reverse=True)
        core_modules = [node for node, _ in sorted_by_centrality[:top_n] if centrality[node] > 0]

        # High coupling: nodes with highest combined in-degree + out-degree
        coupling_scores = {
            node: graph.in_degree(node) + graph.out_degree(node)
            for node in graph.nodes()
        }
        sorted_by_coupling = sorted(coupling_scores.items(), key=lambda x: x[1], reverse=True)
        high_coupling = [node for node, score in sorted_by_coupling[:top_n] if score > 1]

        return {
            "entry_points": entry_points,
            "core_modules": core_modules,
            "high_coupling_modules": high_coupling,
            "total_files": total_files,
            "total_dependencies": total_deps,
        }

    # ------------------------------------------------------------------
    # Persistence helpers
    # ------------------------------------------------------------------

    def _summary_path(self, repo_name: str) -> str:
        safe = repo_name.replace("/", "_")
        return os.path.join(self.arch_dir, f"{safe}.json")

    def _save_summary(self, repo_name: str, summary: Dict[str, Any]) -> None:
        path = self._summary_path(repo_name)
        # Annotate with schema version and build timestamp for staleness detection
        versioned = dict(summary)
        versioned["_schema_version"] = _SUMMARY_SCHEMA_VERSION
        versioned["_built_at"] = int(time.time())
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(versioned, fh, indent=2)
        logger.info("Architecture summary saved to %s", path)

    def _load_summary(self, repo_name: str) -> Optional[Dict[str, Any]]:
        path = self._summary_path(repo_name)
        if not os.path.exists(path):
            return None
        try:
            with open(path, "r", encoding="utf-8") as fh:
                data = json.load(fh)
            # Reject summaries written by older schema versions — they may
            # contain zero-dependency artefacts from pre-implementation runs.
            stored_version = data.get("_schema_version", 0)
            if stored_version < _SUMMARY_SCHEMA_VERSION:
                logger.warning(
                    "Discarding stale architecture summary for %s "
                    "(schema v%d < current v%d)",
                    repo_name,
                    stored_version,
                    _SUMMARY_SCHEMA_VERSION,
                )
                return None
            # Strip internal metadata fields before returning to callers
            return {k: v for k, v in data.items() if not k.startswith("_")}
        except Exception as exc:
            logger.error("Failed to load architecture summary from %s: %s", path, exc)
            return None

    # ------------------------------------------------------------------
    # Misc helpers
    # ------------------------------------------------------------------

    _IGNORED_DIRS = {
        "node_modules", ".git", "dist", "build", ".next",
        "venv", "__pycache__", ".venv",
    }

    def _walk_repo_paths(self, repo_path: str) -> List[str]:
        """Walk repo on disk and return all relative file paths."""
        paths = []
        for root, dirs, files in os.walk(repo_path):
            dirs[:] = [d for d in dirs if d not in self._IGNORED_DIRS]
            for fname in files:
                full = os.path.join(root, fname)
                rel = os.path.relpath(full, repo_path).replace(os.sep, "/")
                paths.append(rel)
        return paths
