import logging
import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

import networkx as nx

from models.architecture_drift import (
    PRDriftResult,
    DependencyEdge,
    CouplingChange,
)
from models.pr_intelligence import ChangedFile
from services.github_service import GitHubService
from services.symbol_service import SymbolService
from services.graph_service import GraphService
from services.architecture_service import ArchitectureService
from services.pr_intelligence_service import PRIntelligenceService
from services.tree_sitter_service import TreeSitterService

logger = logging.getLogger(__name__)


class ArchitectureDriftService:
    """Orchestrates Architecture Drift Detection."""

    def __init__(
        self,
        github_service: Optional[GitHubService] = None,
        symbol_service: Optional[SymbolService] = None,
        graph_service: Optional[GraphService] = None,
        architecture_service: Optional[ArchitectureService] = None,
        pr_intelligence_service: Optional[PRIntelligenceService] = None,
    ) -> None:
        self.github_service = github_service or GitHubService()
        self.symbol_service = symbol_service or SymbolService()
        self.graph_service = graph_service or GraphService()
        self.architecture_service = architecture_service or ArchitectureService()
        self.pr_intelligence_service = pr_intelligence_service or PRIntelligenceService(
            github_service=self.github_service,
            symbol_service=self.symbol_service,
            graph_service=self.graph_service,
            architecture_service=self.architecture_service,
        )
        self.tree_sitter = TreeSitterService()

    def _canonical_cycle(self, cycle: List[str]) -> Tuple[str, ...]:
        """Rotates a list representing a cycle so it starts with the minimum node element."""
        if not cycle:
            return ()
        min_idx = cycle.index(min(cycle))
        return tuple(cycle[min_idx:] + cycle[:min_idx])

    def _get_cycles(self, graph: nx.DiGraph, limit: int = 100) -> List[List[str]]:
        """Extracts simple cycles from a NetworkX directed graph, capped for performance."""
        cycles = []
        try:
            for c in nx.simple_cycles(graph):
                cycles.append(c)
                if len(cycles) >= limit:
                    break
        except Exception as e:
            logger.warning(f"Cycle extraction error: {e}")
        return cycles

    def _is_entry_point_file(self, filename: str, imports: List[str]) -> bool:
        """Determines if a file matches framework/convention entry point rules."""
        basename = os.path.basename(filename).lower()
        if basename in {
            "main.py",
            "__main__.py",
            "app.py",
            "application.py",
            "server.py",
            "index.js",
            "server.js",
            "app.js",
            "main.tsx",
            "app.tsx",
        }:
            return True

        norm_path = filename.replace("\\", "/").lower()
        if norm_path.startswith("app/") or norm_path.startswith("pages/"):
            return True

        # Framework check
        imports_lower = [imp.lower() for imp in imports]
        if "fastapi" in imports_lower or "flask" in imports_lower:
            parts = norm_path.split("/")
            if len(parts) <= 2 or basename in {
                "server.py",
                "wsgi.py",
                "asgi.py",
                "run.py",
            }:
                return True

        return False

    def analyze_drift(self, owner: str, repo: str, pr_number: int) -> PRDriftResult:
        """Compares baseline vs drifted architecture to detect structural drift."""
        repo_fullName = f"{owner}/{repo}"

        # Guard: check if repository is indexed
        if not self.graph_service.graph_exists(repo_fullName):
            raise ValueError(
                f"No dependency graph found for '{repo_fullName}'. "
                "Run repository architecture build first."
            )
        summary = self.architecture_service.get_summary(repo_fullName)
        if not summary:
            raise ValueError(
                f"No architecture summary found for '{repo_fullName}'. "
                "Run repository architecture build first."
            )

        # -------------------------------------------------------------------
        # 1. Fetch PR details and changed files
        # -------------------------------------------------------------------
        metadata = self.github_service.fetch_pull_request_metadata(
            owner, repo, pr_number
        )
        raw_files = self.github_service.fetch_pull_request_files(owner, repo, pr_number)

        changed_files = [
            ChangedFile(
                filename=f["filename"],
                status=f["status"],
                additions=f["additions"],
                deletions=f["deletions"],
                changes=f["changes"],
            )
            for f in raw_files
        ]

        total_additions = metadata.get(
            "additions", sum(cf.additions for cf in changed_files)
        )
        total_deletions = metadata.get(
            "deletions", sum(cf.deletions for cf in changed_files)
        )
        head_sha = metadata.get("head_sha", "")

        # -------------------------------------------------------------------
        # 2. Load Baseline Graph G
        # -------------------------------------------------------------------
        G = self.graph_service.load_graph(repo_fullName)
        if G is None:
            G = nx.DiGraph()

        # -------------------------------------------------------------------
        # 3. Apply Delta Patching to G to build G_after
        # -------------------------------------------------------------------
        G_after = G.copy()

        # Build a temporary file index of all files in the repo (including newly added files)
        file_index = {}
        for node, data in G.nodes(data=True):
            file_index[node] = {"language": data.get("language", "python")}
        for cf in changed_files:
            if cf.status == "added":
                # Guess language based on extension
                ext = os.path.splitext(cf.filename)[1].lower()
                lang = (
                    "python"
                    if ext == ".py"
                    else "javascript"
                    if ext in {".js", ".jsx"}
                    else "typescript"
                    if ext in {".ts", ".tsx"}
                    else "unknown"
                )
                file_index[cf.filename] = {"language": lang}

        # Tracks metadata of parsed files for entry point analysis
        parsed_pr_files: Dict[str, Dict[str, Any]] = {}

        for cf in changed_files:
            norm_fn = cf.filename.replace("\\", "/")

            # Find matching node in G_after (case insensitive matching)
            matching_node = None
            for node in list(G_after.nodes):
                if node.replace("\\", "/").lower() == norm_fn.lower():
                    matching_node = node
                    break

            if cf.status == "removed":
                if matching_node:
                    G_after.remove_node(matching_node)
            elif cf.status in ("added", "modified"):
                # Fetch new content
                try:
                    content = self.github_service.fetch_file_content(
                        repo_fullName, cf.filename, ref=head_sha
                    )
                    parsed_meta = self.tree_sitter.parse_file(cf.filename, content)
                    if parsed_meta:
                        parsed_pr_files[cf.filename] = parsed_meta

                        # Apply graph patch
                        node_name = matching_node or cf.filename
                        if not G_after.has_node(node_name):
                            G_after.add_node(
                                node_name,
                                language=parsed_meta.get("language", "unknown"),
                                type="file",
                            )

                        if cf.status == "modified":
                            # Strip all old outgoing edges
                            old_edges = list(G_after.out_edges(node_name))
                            G_after.remove_edges_from(old_edges)

                        # Add new resolved outgoing edges
                        for imp in parsed_meta.get("imports", []):
                            resolved = GraphService._resolve_import(
                                imp=imp,
                                source_file=node_name,
                                file_index=file_index,
                                language=parsed_meta.get("language", "python"),
                            )
                            if resolved:
                                if not G_after.has_node(resolved):
                                    # Fallback node type
                                    G_after.add_node(
                                        resolved, language="unknown", type="file"
                                    )
                                G_after.add_edge(
                                    node_name, resolved, relationship="imports"
                                )
                except Exception as e:
                    logger.warning(
                        f"Failed to delta patch file {cf.filename} in graph: {e}"
                    )

        # -------------------------------------------------------------------
        # 4. Compare Baseline vs Delta Graph
        # -------------------------------------------------------------------
        # Added and removed dependency edges
        added_edges = G_after.edges() - G.edges()
        removed_edges = G.edges() - G_after.edges()

        added_dependencies = [
            DependencyEdge(source=u, target=v) for u, v in added_edges
        ]
        removed_dependencies = [
            DependencyEdge(source=u, target=v) for u, v in removed_edges
        ]

        # Cycles
        cycles_before = set(self._canonical_cycle(c) for c in self._get_cycles(G))
        cycles_after = set(self._canonical_cycle(c) for c in self._get_cycles(G_after))

        new_cycles = [list(c) for c in (cycles_after - cycles_before)]
        resolved_cycles = [list(c) for c in (cycles_before - cycles_after)]

        # Coupling
        coupling_increase: List[CouplingChange] = []
        coupling_decrease: List[CouplingChange] = []

        all_nodes = set(G.nodes) | set(G_after.nodes)
        for node in all_nodes:
            before_val = G.in_degree(node) + G.out_degree(node) if node in G else 0
            after_val = (
                G_after.in_degree(node) + G_after.out_degree(node)
                if node in G_after
                else 0
            )

            if after_val > before_val:
                coupling_increase.append(
                    CouplingChange(file=node, before=before_val, after=after_val)
                )
            elif after_val < before_val:
                coupling_decrease.append(
                    CouplingChange(file=node, before=before_val, after=after_val)
                )

        # Sort lists by difference size descending
        coupling_increase.sort(key=lambda c: c.after - c.before, reverse=True)
        coupling_decrease.sort(key=lambda c: c.before - c.after, reverse=True)

        # Entry Points
        new_entry_points: List[str] = []
        removed_entry_points: List[str] = []
        baseline_eps = set(summary.entry_points or [])

        # Check for removed entry points
        for cf in changed_files:
            if cf.status == "removed" and cf.filename in baseline_eps:
                removed_entry_points.append(cf.filename)

        # Check for added/modified files that became entry points
        for cf in changed_files:
            if cf.status in ("added", "modified"):
                parsed_meta = parsed_pr_files.get(cf.filename)
                if parsed_meta:
                    imports = parsed_meta.get("imports", [])
                    is_ep = self._is_entry_point_file(cf.filename, imports)
                    if is_ep and cf.filename not in baseline_eps:
                        new_entry_points.append(cf.filename)
                    elif not is_ep and cf.filename in baseline_eps:
                        removed_entry_points.append(cf.filename)

        # -------------------------------------------------------------------
        # 5. Hotspots detection
        # -------------------------------------------------------------------
        baseline_core = set(summary.core_modules or [])
        baseline_coupling = set(summary.high_coupling_modules or [])

        # Centrality
        centrality = {}
        if G.number_of_nodes() > 1:
            centrality = nx.degree_centrality(G)
        else:
            centrality = {n: 0.0 for n in G.nodes}
        sorted_centrality = sorted(centrality.items(), key=lambda x: x[1], reverse=True)
        # Top 15% nodes
        cutoff = max(1, int(len(sorted_centrality) * 0.15))
        top_centrality_nodes = {n for n, _ in sorted_centrality[:cutoff]}

        architectural_hotspots: List[str] = []
        for cf in changed_files:
            if cf.status == "modified":
                cf_lower = cf.filename.replace("\\", "/").lower()
                is_hotspot = False
                # Intersection check
                for item in baseline_eps:
                    if item.replace("\\", "/").lower() == cf_lower:
                        is_hotspot = True
                for item in baseline_core:
                    if item.replace("\\", "/").lower() == cf_lower:
                        is_hotspot = True
                for item in baseline_coupling:
                    if item.replace("\\", "/").lower() == cf_lower:
                        is_hotspot = True
                for item in top_centrality_nodes:
                    if item.replace("\\", "/").lower() == cf_lower:
                        is_hotspot = True

                if is_hotspot:
                    architectural_hotspots.append(cf.filename)

        # -------------------------------------------------------------------
        # 6. Risk Scoring and Improvement Scoring
        # -------------------------------------------------------------------
        # Calculate blast radius via PRIntelligenceService
        # If the call fails, fallback to LOW
        blast_radius_lvl = "LOW"
        impact_radius_val = 0
        try:
            pr_res = self.pr_intelligence_service.analyze_pull_request(
                owner, repo, pr_number
            )
            blast_radius_lvl = pr_res.blast_radius
            impact_radius_val = pr_res.impact_radius
        except Exception:
            pass

        risk_score, risk_level = self._compute_drift_risk(
            new_cycles=new_cycles,
            changed_core_files=[
                f
                for f in baseline_core
                if any(cf.filename.lower() == f.lower() for cf in changed_files)
            ],
            new_entry_points=new_entry_points,
            coupling_increase=coupling_increase,
            blast_radius_level=blast_radius_lvl,
            added_dependencies=added_dependencies,
            removed_entry_points=removed_entry_points,
        )

        improvement_score = self._compute_drift_improvement(
            resolved_cycles=resolved_cycles,
            coupling_decrease=coupling_decrease,
            removed_entry_points=removed_entry_points,
            removed_dependencies=removed_dependencies,
            total_additions=total_additions,
            total_deletions=total_deletions,
        )

        # -------------------------------------------------------------------
        # 7. Drift Categories & Top Findings
        # -------------------------------------------------------------------
        drift_categories = self._compute_drift_categories(
            new_cycles=new_cycles,
            resolved_cycles=resolved_cycles,
            coupling_increase=coupling_increase,
            coupling_decrease=coupling_decrease,
            new_entry_points=new_entry_points,
            removed_entry_points=removed_entry_points,
            added_dependencies=added_dependencies,
            removed_dependencies=removed_dependencies,
        )

        top_findings = self._generate_top_findings(
            new_cycles=new_cycles,
            resolved_cycles=resolved_cycles,
            new_entry_points=new_entry_points,
            removed_entry_points=removed_entry_points,
            coupling_increase=coupling_increase,
            coupling_decrease=coupling_decrease,
            added_dependencies=added_dependencies,
            removed_dependencies=removed_dependencies,
            impact_radius=impact_radius_val,
        )

        return PRDriftResult(
            repo=repo_fullName,
            pr_number=pr_number,
            architecture_risk_score=risk_score,
            architecture_risk_level=risk_level,
            architecture_improvement_score=improvement_score,
            top_findings=top_findings,
            drift_categories=drift_categories,
            architectural_hotspots=architectural_hotspots,
            added_dependencies=added_dependencies,
            removed_dependencies=removed_dependencies,
            new_cycles=new_cycles,
            resolved_cycles=resolved_cycles,
            coupling_increase=coupling_increase,
            coupling_decrease=coupling_decrease,
            new_entry_points=new_entry_points,
            removed_entry_points=removed_entry_points,
            analyzed_at=datetime.now(timezone.utc).isoformat(),
        )

    def _compute_drift_risk(
        self,
        new_cycles: List[List[str]],
        changed_core_files: List[str],
        new_entry_points: List[str],
        coupling_increase: List[CouplingChange],
        blast_radius_level: str,
        added_dependencies: List[DependencyEdge],
        removed_entry_points: List[str],
    ) -> Tuple[int, str]:
        """Calculates deterministic 0-100 risk score and level."""
        score = 0

        # New cycle: 45 pts
        if new_cycles:
            score += 45

        # Core module modified: 15 pts
        if changed_core_files:
            score += 15

        # Entry point added: 10 pts
        if new_entry_points:
            score += 10

        # Coupling increase (any node increases by >= 5): 15 pts
        if any(c.after - c.before >= 5 for c in coupling_increase):
            score += 15

        # High blast radius: 15 pts
        if blast_radius_level in ("HIGH", "EXTREME"):
            score += 15

        # New dependency edge: 10 pts
        if added_dependencies:
            score += 10

        # Entry point removed: 5 pts
        if removed_entry_points:
            score += 5

        risk_score = min(score, 100)

        if risk_score <= 25:
            risk_level = "LOW"
        elif risk_score <= 50:
            risk_level = "MEDIUM"
        elif risk_score <= 75:
            risk_level = "HIGH"
        else:
            risk_level = "CRITICAL"

        return risk_score, risk_level

    def _compute_drift_improvement(
        self,
        resolved_cycles: List[List[str]],
        coupling_decrease: List[CouplingChange],
        removed_entry_points: List[str],
        removed_dependencies: List[DependencyEdge],
        total_additions: int,
        total_deletions: int,
    ) -> int:
        """Calculates deterministic 0-100 improvement score."""
        score = 0

        # Cycle resolved: 45 pts
        if resolved_cycles:
            score += 45

        # Coupling decreased (any node decreases by >= 5): 20 pts
        if any(c.before - c.after >= 5 for c in coupling_decrease):
            score += 20

        # Entry point cleaned up: 15 pts
        if removed_entry_points:
            score += 15

        # Dependency removed: 10 pts
        if removed_dependencies:
            score += 10

        # Codebase size reduction (deletions > additions by >= 50 lines): 10 pts
        if total_deletions - total_additions >= 50:
            score += 10

        return min(score, 100)

    def _compute_drift_categories(
        self,
        new_cycles: List[List[str]],
        resolved_cycles: List[List[str]],
        coupling_increase: List[CouplingChange],
        coupling_decrease: List[CouplingChange],
        new_entry_points: List[str],
        removed_entry_points: List[str],
        added_dependencies: List[DependencyEdge],
        removed_dependencies: List[DependencyEdge],
    ) -> List[str]:
        """Determines active categories for frontend badges."""
        cats = []
        if new_cycles:
            cats.append("CYCLE_INTRODUCED")
        if resolved_cycles:
            cats.append("CYCLE_RESOLVED")
        if any(c.after - c.before >= 5 for c in coupling_increase):
            cats.append("COUPLING_INCREASED")
        if any(c.before - c.after >= 5 for c in coupling_decrease):
            cats.append("COUPLING_DECREASED")
        if new_entry_points:
            cats.append("ENTRY_POINT_ADDED")
        if removed_entry_points:
            cats.append("ENTRY_POINT_REMOVED")
        if added_dependencies:
            cats.append("DEPENDENCY_ADDED")
        if removed_dependencies:
            cats.append("DEPENDENCY_REMOVED")
        return cats

    def _generate_top_findings(
        self,
        new_cycles: List[List[str]],
        resolved_cycles: List[List[str]],
        new_entry_points: List[str],
        removed_entry_points: List[str],
        coupling_increase: List[CouplingChange],
        coupling_decrease: List[CouplingChange],
        added_dependencies: List[DependencyEdge],
        removed_dependencies: List[DependencyEdge],
        impact_radius: int,
    ) -> List[str]:
        """Generates prioritized list of architectural findings."""
        findings = []

        # 1. New cycles (highest severity)
        for cyc in new_cycles[:2]:
            cycle_str = " -> ".join(map(os.path.basename, cyc))
            findings.append(
                f"New dependency cycle introduced: {cycle_str} -> {os.path.basename(cyc[0])}"
            )

        # 2. Entry points
        for ep in new_entry_points[:2]:
            findings.append(f"New entry point created: {os.path.basename(ep)}")
        for ep in removed_entry_points[:2]:
            findings.append(f"Entry point removed: {os.path.basename(ep)}")

        # 3. Coupling increases (difference >= 5)
        for c in coupling_increase:
            diff = c.after - c.before
            if diff >= 5:
                findings.append(
                    f"Coupling increased significantly in {os.path.basename(c.file)} (from {c.before} to {c.after})"
                )

        # 4. Resolved cycles
        if resolved_cycles:
            findings.append(
                f"Dependency cycle resolved ({len(resolved_cycles)} loops broken)"
            )

        # 5. Coupling decreases
        for c in coupling_decrease[:2]:
            diff = c.before - c.after
            if diff >= 5:
                findings.append(
                    f"Coupling decreased in {os.path.basename(c.file)} (from {c.before} to {c.after})"
                )

        # 6. High blast radius info
        if impact_radius >= 16:
            findings.append(
                f"High blast radius detected ({impact_radius} downstream files affected)"
            )

        # 7. Added dependencies
        for edge in added_dependencies[:2]:
            findings.append(
                f"New dependency introduced: {os.path.basename(edge.source)} -> {os.path.basename(edge.target)}"
            )

        # 8. Removed dependencies
        for edge in removed_dependencies[:2]:
            findings.append(
                f"Dependency removed: {os.path.basename(edge.source)} -> {os.path.basename(edge.target)}"
            )

        return findings[:10]
