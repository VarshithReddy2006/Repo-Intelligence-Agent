import logging
import os
import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set, Tuple

import networkx as nx

from models.pr_intelligence import (
    PRAnalysisResult,
    ChangedFile,
    SymbolChange,
    PropagationPath,
    RiskBreakdown,
    ReviewFocusArea,
)
from services.github_service import GitHubService
from services.symbol_service import SymbolService
from services.graph_service import GraphService
from services.architecture_service import ArchitectureService
from services.impact_analysis_service import ImpactAnalysisService

logger = logging.getLogger(__name__)


class PRIntelligenceService:
    """Orchestrates Pull Request Intelligence Analysis."""

    def __init__(
        self,
        github_service: Optional[GitHubService] = None,
        symbol_service: Optional[SymbolService] = None,
        graph_service: Optional[GraphService] = None,
        architecture_service: Optional[ArchitectureService] = None,
    ) -> None:
        self.github_service = github_service or GitHubService()
        self.symbol_service = symbol_service or SymbolService()
        self.graph_service = graph_service or GraphService()
        self.architecture_service = architecture_service or ArchitectureService()

    def classify_pr_size(self, changed_files_count: int, total_lines_changed: int, changed_symbol_count: int) -> str:
        """Determines PR size based on files, symbols, and lines changed.

        XS: 0-20, S: 21-40, M: 41-60, L: 61-80, XL: 81-100.
        """
        file_score = min(changed_files_count * 3, 30)
        symbol_score = min(changed_symbol_count * 1.5, 30)
        line_score = min(total_lines_changed * 0.1, 40)

        size_score = file_score + symbol_score + line_score

        if size_score <= 20:
            return "XS"
        elif size_score <= 40:
            return "S"
        elif size_score <= 60:
            return "M"
        elif size_score <= 80:
            return "L"
        else:
            return "XL"

    def classify_blast_radius(self, impact_radius: int, max_depth: int) -> str:
        """Classifies the blast radius based on affected file count and depth."""
        if impact_radius <= 5:
            base = "LOW"
        elif impact_radius <= 15:
            base = "MEDIUM"
        elif impact_radius <= 30:
            base = "HIGH"
        else:
            base = "EXTREME"

        # Depth promotion
        if max_depth >= 3:
            if base == "LOW":
                return "MEDIUM"
            elif base == "MEDIUM":
                return "HIGH"
            elif base == "HIGH":
                return "EXTREME"

        return base

    def analyze_pull_request(self, owner: str, repo: str, pr_number: int) -> PRAnalysisResult:
        """Runs the 7-stage PR analysis pipeline.

        Raises:
            ValueError: If repository is not indexed or analysis fails.
        """
        repo_fullName = f"{owner}/{repo}"

        # Guard: Check if graph/index exists
        if not self.graph_service.graph_exists(repo_fullName):
            raise ValueError(
                f"No dependency graph found for '{repo_fullName}'. "
                "Run repository architecture build first."
            )
        if not self.symbol_service.index_exists(repo_fullName):
            raise ValueError(
                f"No symbol index found for '{repo_fullName}'. "
                "Run repository architecture build first."
            )

        # -------------------------------------------------------------------
        # 1. Fetch PR metadata and changed files
        # -------------------------------------------------------------------
        metadata = self.github_service.fetch_pull_request_metadata(owner, repo, pr_number)
        raw_files = self.github_service.fetch_pull_request_files(owner, repo, pr_number)

        changed_files = [
            ChangedFile(
                filename=f["filename"],
                status=f["status"],
                additions=f["additions"],
                deletions=f["deletions"],
                changes=f["changes"]
            )
            for f in raw_files
        ]

        total_additions = metadata.get("additions", sum(cf.additions for cf in changed_files))
        total_deletions = metadata.get("deletions", sum(cf.deletions for cf in changed_files))
        head_sha = metadata.get("head_sha", "")

        # Stage 1 — GitHub Response Diagnostics
        logger.info(
            "[PR DIAGNOSTICS] PR #%s summary: files=%s additions=%s deletions=%s",
            pr_number,
            metadata.get("changed_files"),
            metadata.get("additions"),
            metadata.get("deletions"),
        )
        logger.info(
            "[PR DIAGNOSTICS] GitHub returned %d changed files",
            len(raw_files),
        )
        logger.info(
            "[PR DIAGNOSTICS] Changed file names: %s",
            [f.get("filename") for f in raw_files],
        )

        # Stage 2 — File Mapping Diagnostics
        logger.info(
            "[PR DIAGNOSTICS] GitHub files=%d mapped files=%d",
            len(raw_files),
            len(changed_files),
        )
        logger.info(
            "[PR DIAGNOSTICS] Normalized changed files: %s",
            changed_files,
        )

        # -------------------------------------------------------------------
        # 2. Compute symbol diff
        # -------------------------------------------------------------------
        symbol_index = self.symbol_service.load(repo_fullName)
        added_symbols: List[SymbolChange] = []
        modified_symbols: List[SymbolChange] = []
        removed_symbols: List[SymbolChange] = []

        changed_filenames = {cf.filename for cf in changed_files}

        # For modified and removed files, map to their existing symbols in the index
        if symbol_index:
            for symbol in symbol_index.symbols:
                # Normalise separator
                sym_file_norm = symbol.file_path.replace("\\", "/")
                for cf in changed_files:
                    cf_norm = cf.filename.replace("\\", "/")
                    if sym_file_norm == cf_norm:
                        sc = SymbolChange(
                            name=symbol.name,
                            type=symbol.type,
                            file_path=symbol.file_path,
                            line_number=symbol.line_number,
                            language=symbol.language,
                            change_type=cf.status if cf.status in {"added", "removed", "modified"} else "modified",
                            parent_class=symbol.parent_class
                        )
                        if cf.status == "removed":
                            removed_symbols.append(sc)
                        elif cf.status == "modified":
                            modified_symbols.append(sc)

        # For added files, since they aren't in the current symbol index, try to fetch content and parse
        for cf in changed_files:
            if cf.status == "added":
                try:
                    content = self.github_service.fetch_file_content(repo_fullName, cf.filename, ref=head_sha)
                    parsed_syms = self.symbol_service._extract_file_symbols(cf.filename, content)
                    for sym in parsed_syms:
                        added_symbols.append(
                            SymbolChange(
                                name=sym.name,
                                type=sym.type,
                                file_path=sym.file_path,
                                line_number=sym.line_number,
                                language=sym.language,
                                change_type="added",
                                parent_class=sym.parent_class
                            )
                        )
                except Exception as e:
                    logger.warning(f"Could not fetch/parse symbols for added file {cf.filename}: {e}")

        total_changed_symbols = len(added_symbols) + len(modified_symbols) + len(removed_symbols)

        # Stage 3 — Symbol Extraction Diagnostics
        logger.info(
            "[PR DIAGNOSTICS] Symbol index size=%d",
            len(symbol_index.symbols) if (symbol_index and hasattr(symbol_index, "symbols")) else 0,
        )
        logger.info(
            "[PR DIAGNOSTICS] Matched symbols: added=%d modified=%d removed=%d",
            len(added_symbols),
            len(modified_symbols),
            len(removed_symbols),
        )

        # -------------------------------------------------------------------
        # 3. Traverse dependency graph (BFS) to find affected files (blast radius)
        # -------------------------------------------------------------------
        graph = self.graph_service.load_graph(repo_fullName)
        
        # Stage 4 — Dependency Graph Diagnostics
        logger.info(
            "[PR DIAGNOSTICS] Dependency graph nodes=%d edges=%d",
            graph.number_of_nodes() if graph else 0,
            graph.number_of_edges() if graph else 0,
        )
        affected_files_set: Set[str] = set()

        if graph:
            for cf in changed_files:
                # Normalise changed file paths to match graph nodes
                norm_fn = cf.filename.replace("\\", "/")
                # Find matching graph node (case insensitive, path separators normalised)
                matching_node = None
                for node in graph.nodes:
                    if node.replace("\\", "/").lower() == norm_fn.lower():
                        matching_node = node
                        break
                
                if matching_node:
                    # Direction 'reverse' walks backwards (who imports this file)
                    visited = ImpactAnalysisService._bfs(graph, matching_node, direction="reverse", depth=4)
                    affected_files_set.update(visited)

            # Exclude the seed files from the affected files list
            seed_nodes = set()
            for cf in changed_files:
                norm_fn = cf.filename.replace("\\", "/")
                for node in graph.nodes:
                    if node.replace("\\", "/").lower() == norm_fn.lower():
                        seed_nodes.add(node)
            affected_files_set -= seed_nodes

        affected_files = sorted(list(affected_files_set))
        impact_radius = len(affected_files)

        # -------------------------------------------------------------------
        # 4. Build propagation paths
        # -------------------------------------------------------------------
        propagation_paths: List[PropagationPath] = []
        max_depth = 0

        if graph and affected_files:
            # We want to trace paths from affected files (consumers) back to changed files (dependencies)
            # A -> B represents A imports B. So shortest path from A to B is the propagation path.
            for aff in affected_files:
                for cf in changed_files:
                    norm_cf = cf.filename.replace("\\", "/")
                    matching_seed = None
                    for node in graph.nodes:
                        if node.replace("\\", "/").lower() == norm_cf.lower():
                            matching_seed = node
                            break
                    if matching_seed:
                        try:
                            path = nx.shortest_path(graph, source=aff, target=matching_seed)
                            if len(path) >= 2:
                                depth = len(path) - 1
                                propagation_paths.append(
                                    PropagationPath(
                                        source=matching_seed,
                                        target=aff,
                                        path=path,
                                        depth=depth
                                    )
                                )
                                max_depth = max(max_depth, depth)
                        except (nx.NetworkXNoPath, nx.NodeNotFound):
                            pass

            # Sort by depth descending and limit to 10 paths for payload efficiency
            propagation_paths.sort(key=lambda p: p.depth, reverse=True)
            propagation_paths = propagation_paths[:10]

        # Stage 5 — Blast Radius Diagnostics
        logger.info(
            "[PR DIAGNOSTICS] Graph nodes count=%d affected files=%d",
            graph.number_of_nodes() if graph else 0,
            len(affected_files) if 'affected_files' in locals() else 0,
        )
        logger.info(
            "[PR DIAGNOSTICS] Impact radius=%d max_depth=%d",
            impact_radius if 'impact_radius' in locals() else 0,
            max_depth if 'max_depth' in locals() else 0,
        )

        # -------------------------------------------------------------------
        # 5. Extract critical graph categories
        # -------------------------------------------------------------------
        arch_summary = self.architecture_service.get_summary(repo_fullName)
        
        changed_entry_points: List[str] = []
        changed_core_files: List[str] = []
        changed_high_coupling_files: List[str] = []
        
        core_set = set()
        coupling_set = set()
        entry_set = set()

        if arch_summary:
            core_set = {f.replace("\\", "/").lower() for f in (arch_summary.core_modules or [])}
            coupling_set = {f.replace("\\", "/").lower() for f in (arch_summary.high_coupling_modules or [])}
            entry_set = {f.replace("\\", "/").lower() for f in (arch_summary.entry_points or [])}

            for cf in changed_files:
                cf_lower = cf.filename.replace("\\", "/").lower()
                if cf_lower in entry_set:
                    changed_entry_points.append(cf.filename)
                if cf_lower in core_set:
                    changed_core_files.append(cf.filename)
                if cf_lower in coupling_set:
                    changed_high_coupling_files.append(cf.filename)

        # -------------------------------------------------------------------
        # 6. Compute 0-100 risk score and top risks
        # -------------------------------------------------------------------
        risk_score, risk_level, risk_breakdown, top_risks = self._compute_risk_and_explanations(
            changed_files=changed_files,
            changed_symbols_count=total_changed_symbols,
            changed_entry_points=changed_entry_points,
            changed_core_files=changed_core_files,
            changed_high_coupling_files=changed_high_coupling_files,
            impact_radius=impact_radius,
            max_depth=max_depth,
            removed_symbols_count=len(removed_symbols),
            total_graph_nodes=graph.number_of_nodes() if graph else 1
        )

        # -------------------------------------------------------------------
        # 7. Size & Blast Radius Classification
        # -------------------------------------------------------------------
        pr_size = self.classify_pr_size(
            changed_files_count=len(changed_files),
            total_lines_changed=total_additions + total_deletions,
            changed_symbol_count=total_changed_symbols
        )

        blast_radius = self.classify_blast_radius(impact_radius, max_depth)

        # -------------------------------------------------------------------
        # 8. Component and focus area detection
        # -------------------------------------------------------------------
        all_touched_files = [cf.filename for cf in changed_files] + affected_files
        affected_components = ImpactAnalysisService._detect_components(all_touched_files)

        review_focus_areas = self._generate_review_focus_areas(
            changed_files=changed_files,
            changed_entry_points=changed_entry_points,
            changed_core_files=changed_core_files,
            changed_high_coupling_files=changed_high_coupling_files,
            removed_symbols=removed_symbols,
            pr_size=pr_size
        )

        return PRAnalysisResult(
            repo=repo_fullName,
            pr_number=pr_number,
            pr_url=metadata.get("html_url", f"https://github.com/{repo_fullName}/pull/{pr_number}"),
            pr_title=metadata.get("title", ""),
            pr_state=metadata.get("state", "open"),
            pr_size=pr_size,
            risk_score=risk_score,
            risk_level=risk_level,
            risk_breakdown=risk_breakdown,
            top_risks=top_risks,
            changed_files=changed_files,
            total_additions=total_additions,
            total_deletions=total_deletions,
            added_symbols=added_symbols,
            modified_symbols=modified_symbols,
            removed_symbols=removed_symbols,
            affected_files=affected_files,
            impact_radius=impact_radius,
            blast_radius=blast_radius,
            max_depth=max_depth,
            propagation_paths=propagation_paths,
            affected_components=affected_components,
            changed_entry_points=changed_entry_points,
            changed_core_files=changed_core_files,
            changed_high_coupling_files=changed_high_coupling_files,
            review_focus_areas=review_focus_areas,
            analyzed_at=datetime.now(timezone.utc).isoformat()
        )

    def _compute_risk_and_explanations(
        self,
        changed_files: List[ChangedFile],
        changed_symbols_count: int,
        changed_entry_points: List[str],
        changed_core_files: List[str],
        changed_high_coupling_files: List[str],
        impact_radius: int,
        max_depth: int,
        removed_symbols_count: int,
        total_graph_nodes: int
    ) -> Tuple[int, str, List[RiskBreakdown], List[str]]:
        """Computes deterministic 0-100 risk score, breakdown, and top risks."""
        breakdown: List[RiskBreakdown] = []
        raw_top_risks: List[Tuple[str, int]] = []

        # 1. Changed file count (Max 15)
        files_count = len(changed_files)
        if files_count >= 16:
            file_pts = 15
        elif files_count >= 9:
            file_pts = 12
        elif files_count >= 4:
            file_pts = 8
        else:
            file_pts = 3
        breakdown.append(RiskBreakdown(factor="Changed file count", score=file_pts, detail=f"{files_count} files changed"))
        if file_pts >= 8:
            raw_top_risks.append((f"Large number of changed files ({files_count})", file_pts))

        # 2. Changed symbol count (Max 10)
        if changed_symbols_count >= 31:
            sym_pts = 10
        elif changed_symbols_count >= 16:
            sym_pts = 8
        elif changed_symbols_count >= 6:
            sym_pts = 5
        else:
            sym_pts = 2
        breakdown.append(RiskBreakdown(factor="Changed symbol count", score=sym_pts, detail=f"{changed_symbols_count} symbols changed"))
        if sym_pts >= 8:
            raw_top_risks.append((f"Large number of symbol modifications ({changed_symbols_count})", sym_pts))

        # 3. Core module modified (Max 20)
        core_count = len(changed_core_files)
        core_pts = min(core_count * 10, 20)
        breakdown.append(RiskBreakdown(factor="Core module modified", score=core_pts, detail=f"{core_count} core files modified"))
        if core_pts > 0:
            raw_top_risks.append((f"Core module modified ({', '.join(map(os.path.basename, changed_core_files[:2]))})", core_pts))

        # 4. Entry point modified (Max 15)
        entry_pts = 15 if changed_entry_points else 0
        breakdown.append(RiskBreakdown(factor="Entry point modified", score=entry_pts, detail=f"{len(changed_entry_points)} entry points modified"))
        if entry_pts > 0:
            raw_top_risks.append((f"Entry point modified ({', '.join(map(os.path.basename, changed_entry_points[:2]))})", entry_pts))

        # 5. High coupling file modified (Max 10)
        coupling_count = len(changed_high_coupling_files)
        coupling_pts = min(coupling_count * 5, 10)
        breakdown.append(RiskBreakdown(factor="High-coupling file modified", score=coupling_pts, detail=f"{coupling_count} high-coupling files modified"))
        if coupling_pts > 0:
            raw_top_risks.append((f"High-coupling file modified ({', '.join(map(os.path.basename, changed_high_coupling_files[:2]))})", coupling_pts))

        # 6. Impact radius (Max 15)
        # (impact_radius / total_files_in_repo) * 15, capped at 15
        impact_ratio = (impact_radius / total_graph_nodes) if total_graph_nodes > 0 else 0
        impact_pts = min(int(impact_ratio * 15), 15)
        breakdown.append(RiskBreakdown(factor="Impact radius", score=impact_pts, detail=f"{impact_radius} downstream files affected ({int(impact_ratio * 100)}%)"))
        if impact_pts >= 5:
            raw_top_risks.append((f"{impact_radius} downstream files affected", impact_pts))

        # 7. Dependency depth (Max 10)
        if max_depth >= 4:
            depth_pts = 10
        elif max_depth == 3:
            depth_pts = 7
        elif max_depth == 2:
            depth_pts = 4
        else:
            depth_pts = 0
        breakdown.append(RiskBreakdown(factor="Dependency depth", score=depth_pts, detail=f"Max propagation depth: {max_depth}"))
        if depth_pts > 0:
            raw_top_risks.append((f"Deep dependency propagation (depth {max_depth})", depth_pts))

        # 8. Symbol removal (Max 5)
        removal_pts = 5 if removed_symbols_count > 0 else 0
        breakdown.append(RiskBreakdown(factor="Symbol removal", score=removal_pts, detail=f"{removed_symbols_count} symbols removed"))
        if removal_pts > 0:
            raw_top_risks.append(("Public symbol removal detected", removal_pts))

        # Sum and cap at 100
        total_score = min(sum(r.score for r in breakdown), 100)

        # Risk level
        if total_score <= 25:
            risk_level = "LOW"
        elif total_score <= 50:
            risk_level = "MEDIUM"
        elif total_score <= 75:
            risk_level = "HIGH"
        else:
            risk_level = "CRITICAL"

        # Sort top risks by highest points descending
        raw_top_risks.sort(key=lambda r: r[1], reverse=True)
        top_risks = [r[0] for r in raw_top_risks[:5]]

        return total_score, risk_level, breakdown, top_risks

    def _generate_review_focus_areas(
        self,
        changed_files: List[ChangedFile],
        changed_entry_points: List[str],
        changed_core_files: List[str],
        changed_high_coupling_files: List[str],
        removed_symbols: List[SymbolChange],
        pr_size: str
    ) -> List[ReviewFocusArea]:
        """Generates rule-based ReviewFocusArea checklists."""
        areas: List[ReviewFocusArea] = []

        if changed_entry_points:
            areas.append(
                ReviewFocusArea(
                    area="API Backward Compatibility",
                    reason="Modified entry point files can break consumer integrations. Verify API contracts, payload formats, and query parameters.",
                    files=changed_entry_points,
                    priority="HIGH"
                )
            )

        if changed_core_files:
            areas.append(
                ReviewFocusArea(
                    area="Core Business Logic Check",
                    reason="Modifications to core modules affect multiple subsystem components. Review side-effects and run integration test suites.",
                    files=changed_core_files,
                    priority="HIGH"
                )
            )

        if changed_high_coupling_files:
            areas.append(
                ReviewFocusArea(
                    area="Coupling Dependency Cascade",
                    reason="High coupling files can trigger cascading changes. Check if changes require updates in importing components.",
                    files=changed_high_coupling_files,
                    priority="MEDIUM"
                )
            )

        if removed_symbols:
            areas.append(
                ReviewFocusArea(
                    area="Removed Symbol Contract Check",
                    reason="Removed public functions, classes, or methods can break import calls in importing files. Confirm no references remain.",
                    files=sorted(list({s.file_path for s in removed_symbols})),
                    priority="HIGH"
                )
            )

        if pr_size in {"L", "XL"}:
            areas.append(
                ReviewFocusArea(
                    area="Large PR Review Partitioning",
                    reason=f"PR size is {pr_size}. Reviewing large PRs increases bug slip-through. Consider splitting into smaller commits or PRs.",
                    files=[cf.filename for cf in changed_files],
                    priority="MEDIUM"
                )
            )

        # Check for model/schema changes
        model_files = [
            cf.filename for cf in changed_files
            if re.search(r"model|schema|pydantic|dto", cf.filename.lower())
        ]
        if model_files:
            areas.append(
                ReviewFocusArea(
                    area="Database Schema & Model Migrations",
                    reason="Data models or schemas changed. Verify serialization, database migrations, and backward compatibility with cached payloads.",
                    files=model_files,
                    priority="HIGH"
                )
            )

        # Frontend changes check
        frontend_files = [
            cf.filename for cf in changed_files
            if re.search(r"front|ui|\.tsx|\.jsx|\.html|\.css", cf.filename.lower())
        ]
        if frontend_files:
            areas.append(
                ReviewFocusArea(
                    area="Frontend UI Visual Verification",
                    reason="User interface layouts or components changed. Perform visual regression checking and check responsive layout views.",
                    files=frontend_files,
                    priority="LOW"
                )
            )

        # Test coverage warning
        has_tests = any(re.search(r"test|spec|mock", cf.filename.lower()) for cf in changed_files)
        if changed_files and not has_tests:
            areas.append(
                ReviewFocusArea(
                    area="Missing Unit/Integration Tests",
                    reason="Source code files changed but no corresponding test files were modified. Ensure coverage is added for new behavior.",
                    files=[],
                    priority="MEDIUM"
                )
            )

        return areas
