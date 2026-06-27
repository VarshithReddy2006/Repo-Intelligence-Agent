"""Execution scheduler for grouping BuildTasks into sequential stages of parallelizable work (PH2-022)."""

from __future__ import annotations

import logging
from typing import Dict, List

from core.analysis_registry import AnalysisRegistry
from core.incremental_build_planner import BuildTask

logger = logging.getLogger(__name__)


class ExecutionScheduler:
    """Schedules BuildTasks into topological execution stages to maximize parallelism."""

    @staticmethod
    def schedule(
        tasks: List[BuildTask], registry: AnalysisRegistry
    ) -> List[List[BuildTask]]:
        """Groups tasks into stages using dynamic level assignment based on DAG dependencies.

        Within each stage, tasks are sorted alphabetically by their analysis name to ensure
        deterministic execution and event ordering.
        """
        task_map = {t.analysis: t for t in tasks}
        stages_indices: Dict[str, int] = {}

        def get_stage_index(name: str) -> int:
            if name in stages_indices:
                return stages_indices[name]

            node = registry.nodes.get(name)
            if not node:
                stages_indices[name] = 0
                return 0

            # Filter dependencies to only those that are scheduled in the plan
            relevant_deps = [dep for dep in node.dependencies if dep in task_map]
            if not relevant_deps:
                stages_indices[name] = 0
                return 0

            # Stage index is 1 + max of dependency stage indices
            stages_indices[name] = 1 + max(
                get_stage_index(dep) for dep in relevant_deps
            )
            return stages_indices[name]

        # Calculate stage index for each task
        for task in tasks:
            get_stage_index(task.analysis)

        # Group tasks by stage index
        grouped: Dict[int, List[BuildTask]] = {}
        for task in tasks:
            idx = stages_indices[task.analysis]
            if idx not in grouped:
                grouped[idx] = []
            grouped[idx].append(task)

        # Construct sorted list of stages
        stages: List[List[BuildTask]] = []
        for idx in sorted(grouped.keys()):
            # Sort tasks within each stage alphabetically by name for determinism
            stage_tasks = sorted(grouped[idx], key=lambda t: t.analysis)
            stages.append(stage_tasks)

        logger.info(
            "Scheduled %d build tasks into %d parallel stages.",
            len(tasks),
            len(stages),
        )
        return stages
