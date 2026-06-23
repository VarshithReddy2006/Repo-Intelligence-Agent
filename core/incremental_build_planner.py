"""Incremental build planner for deciding FULL, PARTIAL, or SKIP modes (PH2-021)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Literal, Optional, Set

from core.analysis_registry import AnalysisNode, AnalysisRegistry
from core.change_detector import ChangeSet
from models.build_manifest import BuildManifest


@dataclass
class BuildTask:
    """A task representing the build mode and scope for a specific analysis node."""

    analysis: str
    mode: Literal["FULL", "PARTIAL", "SKIP"]
    changed_files: Set[str]
    dependencies: List[str]


class IncrementalBuildPlanner:
    """Planner that generates a sequence of BuildTasks based on file changes and the DAG."""

    @staticmethod
    def _snapshot_exists(
        node: AnalysisNode,
        repo_name: str,
        snapshot_store: Any,
        graph_service: Any,
    ) -> bool:
        """Check if the physical snapshot/graph for a node exists on disk."""
        if node.name == "Symbol Index":
            return snapshot_store.exists(repo_name, "symbols")
        elif node.name == "Dependency Graph":
            return graph_service.graph_exists(repo_name)
        elif node.name == "Call Graph":
            return graph_service.graph_exists(f"{repo_name}_call_graph")
        elif node.name == "Git History":
            return snapshot_store.exists(repo_name, "churn", subkey="30d")
        elif node.name == "API Surface":
            return snapshot_store.exists(repo_name, "api_surface")
        else:
            key = node.outputs[0] if node.outputs else node.name.lower()
            return snapshot_store.exists(repo_name, key)

    @classmethod
    def plan(
        cls,
        repo_name: str,
        change_set: ChangeSet,
        registry: AnalysisRegistry,
        old_manifest: Optional[BuildManifest],
        snapshot_store: Any,
        graph_service: Any,
        force_rebuild: bool = False,
    ) -> List[BuildTask]:
        """Generate a build plan containing BuildTasks in topological order."""
        nodes = registry.get_build_order()
        tasks: List[BuildTask] = []
        task_modes: Dict[str, Literal["FULL", "PARTIAL", "SKIP"]] = {}

        # Collect changed code files
        supported_exts = {".py", ".js", ".jsx", ".ts", ".tsx"}
        all_changed_files = (
            change_set.added | change_set.modified | change_set.deleted | set(change_set.renamed.keys()) | set(change_set.renamed.values())
        )
        changed_code_files = {f for f in all_changed_files if any(f.endswith(ext) for ext in supported_exts)}

        for node in nodes:
            # 1. Force rebuild -> FULL
            if force_rebuild:
                mode = "FULL"
            # 2. No old manifest -> FULL
            elif old_manifest is None:
                mode = "FULL"
            # 3. Missing snapshot -> FULL
            elif not cls._snapshot_exists(node, repo_name, snapshot_store, graph_service):
                mode = "FULL"
            # 4. Stale schema version -> FULL
            else:
                stored_version = old_manifest.schema_versions.get(node.name) or old_manifest.snapshot_versions.get(node.name)
                if stored_version is None or stored_version < node.schema_version:
                    mode = "FULL"
                else:
                    # Snapshot exists and is up to date. Check if we need a partial rebuild or skip.
                    if node.name == "Symbol Index":
                        if changed_code_files:
                            mode = "PARTIAL"
                        else:
                            mode = "SKIP"
                    else:
                        # For other nodes, run PARTIAL if any of their dependencies are running (not SKIP)
                        dep_running = any(
                            task_modes.get(dep, "SKIP") != "SKIP"
                            for dep in node.dependencies
                        )
                        if dep_running:
                            mode = "PARTIAL"
                        else:
                            mode = "SKIP"

            task_modes[node.name] = mode
            tasks.append(
                BuildTask(
                    analysis=node.name,
                    mode=mode,
                    changed_files=changed_code_files if mode != "SKIP" else set(),
                    dependencies=node.dependencies,
                )
            )

        return tasks
