"""Architecture Context Service — Phase 2.

Provides a thin helper that loads the Phase 1 architecture summary for a
repository and returns it as an ArchContext model ready for LLM prompt
injection.

Used by:
  - RetrievalService.retrieve_and_answer()
  - IssueMapper.map_issue()
  - Chat endpoint (via api.py)

If no architecture summary exists for the given repo (the user hasn't run
/api/architecture/build yet) the service returns an ArchContext with
available=False, so callers degrade gracefully without crashing.
"""

import logging
from typing import Optional

from models.phase2 import ArchContext
from services.architecture_service import ArchitectureService

logger = logging.getLogger(__name__)

# Shared default instance — callers can override by passing their own.
_default_arch_service: Optional[ArchitectureService] = None


def _get_arch_service() -> ArchitectureService:
    global _default_arch_service
    if _default_arch_service is None:
        _default_arch_service = ArchitectureService()
    return _default_arch_service


class ArchContextService:
    """Loads architecture summaries and converts them to injection-ready ArchContext objects."""

    def __init__(self, architecture_service: Optional[ArchitectureService] = None) -> None:
        self._arch_service = architecture_service or _get_arch_service()

    def get_context(self, repo_name: str) -> ArchContext:
        """Load the architecture context for a repository.

        Args:
            repo_name: Repository identifier (owner/repo).

        Returns:
            ArchContext with available=True when data exists,
            ArchContext with available=False when no summary is found.
        """
        try:
            summary = self._arch_service.get_summary(repo_name)
            if summary is None:
                logger.debug(
                    "No architecture summary for '%s' — context injection disabled.", repo_name
                )
                return ArchContext(available=False)

            return ArchContext(
                entry_points=summary.entry_points,
                core_modules=summary.core_modules,
                high_coupling_modules=summary.high_coupling_modules,
                total_files=summary.total_files,
                total_dependencies=summary.total_dependencies,
                available=True,
            )
        except Exception as exc:
            logger.warning(
                "Failed to load architecture context for '%s': %s", repo_name, exc
            )
            return ArchContext(available=False)
