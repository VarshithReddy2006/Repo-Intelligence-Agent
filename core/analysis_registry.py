"""Analysis service registry and DAG validator (PH2-002)."""

from __future__ import annotations

from typing import Any, Dict, List, Set, Type


class AnalysisNode:
    """A single node in the analysis dependency DAG."""

    def __init__(
        self,
        name: str,
        service_class: Type[Any],
        dependencies: List[str],
        outputs: List[str],
        schema_version: int,
    ) -> None:
        self.name = name
        self.service_class = service_class
        self.dependencies = dependencies
        self.outputs = outputs
        self.schema_version = schema_version


class AnalysisRegistry:
    """Registry representing the dependency DAG of analysis services."""

    def __init__(self) -> None:
        self.nodes: Dict[str, AnalysisNode] = {}

    def register(
        self,
        name: str,
        service_class: Type[Any],
        dependencies: List[str],
        outputs: List[str],
        schema_version: int = 1,
    ) -> None:
        """Register an analysis builder node."""
        self.nodes[name] = AnalysisNode(
            name, service_class, dependencies, outputs, schema_version
        )

    def validate(self) -> None:
        """Validate dependencies: ensure all listed dependencies exist."""
        for name, node in self.nodes.items():
            for dep in node.dependencies:
                if dep not in self.nodes:
                    raise ValueError(
                        f"Dependency '{dep}' declared by analysis node "
                        f"'{name}' is not registered."
                    )

    def get_topological_order(self) -> List[str]:
        """Compute the topological order of registered builders."""
        self.validate()

        visited: Set[str] = set()
        temp_visited: Set[str] = set()
        order: List[str] = []

        def visit(name: str) -> None:
            if name in temp_visited:
                raise ValueError(
                    f"Cycle detected in analysis registry dependencies "
                    f"involving node '{name}'."
                )
            if name not in visited:
                temp_visited.add(name)
                for dep in self.nodes[name].dependencies:
                    visit(dep)
                temp_visited.remove(name)
                visited.add(name)
                order.append(name)

        for name in self.nodes:
            if name not in visited:
                visit(name)

        return order

    def get_build_order(self) -> List[AnalysisNode]:
        """Return the sequence of analysis builder nodes in build order."""
        order = self.get_topological_order()
        return [self.nodes[name] for name in order]
