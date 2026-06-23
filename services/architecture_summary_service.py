"""Architecture Summary Service.

Encapsulates the LLM call that was previously an inline async function
(``generate_architecture_summary_with_llm``) inside ``backend/api.py``.

Keeping this here makes it independently testable, removes an async helper
from the API layer, and isolates the LLM prompt from routing logic.
"""

import json
import logging
from typing import List

from models.schemas import ArchitectureSummary, ComponentRelationship
from services.llm import ProviderFactory

logger = logging.getLogger(__name__)


async def generate_architecture_summary(
    repo_name: str,
    tech_stack: List[str],
    file_paths: List[str],
) -> ArchitectureSummary:
    """Generate an ArchitectureSummary using the configured LLM provider.

    Calls the LLM with the repository name, detected tech stack, and a
    truncated file path list (up to 100 paths).  On any failure the method
    returns a minimal fallback summary rather than raising, so the analysis
    pipeline is never blocked by an LLM outage.

    Args:
        repo_name:   Repository identifier (``owner/repo``).
        tech_stack:  List of detected language/framework names.
        file_paths:  List of relative file paths in the repository.

    Returns:
        A populated :class:`~models.schemas.ArchitectureSummary` instance.
    """
    provider = ProviderFactory.get_provider()

    system_instruction = (
        "You are an expert architecture explainer agent. "
        "Summarise the architecture of this repository, map its components, "
        "and recommend a file reading order. "
        "Return the output in JSON format conforming to the ArchitectureSummary schema."
    )

    truncated_files = file_paths[:100]
    prompt = (
        f"Repository Name: {repo_name}\n"
        f"Detected Tech Stack: {tech_stack}\n"
        f"Repository File Paths (truncated to 100): {truncated_files}\n\n"
        "Explain the architecture, suggest a 3-5 file reading order, and specify "
        "2-3 component relationships. "
        "Ensure your output is a JSON object matching this schema:\n"
        "{\n"
        '  "summary": "high-level text summary",\n'
        '  "reading_order": ["path/to/file1", "path/to/file2"],\n'
        '  "relationships": [\n'
        '    {"source": "src/main.py", "target": "models/schemas.py",'
        ' "relationship_type": "imports", "description": "..."}\n'
        "  ]\n"
        "}\n"
    )

    try:
        raw = await provider.generate(
            prompt=prompt,
            system_instruction=system_instruction,
            response_mime_type="application/json",
        )
        data = json.loads(raw)
        relationships = [
            ComponentRelationship(
                source=r.get("source", ""),
                target=r.get("target", ""),
                relationship_type=r.get("relationship_type", ""),
                description=r.get("description", ""),
            )
            for r in data.get("relationships", [])
        ]
        return ArchitectureSummary(
            summary=data.get("summary", ""),
            reading_order=data.get("reading_order", []),
            relationships=relationships,
        )
    except Exception as exc:
        logger.warning("Failed to generate architecture summary with LLM: %s", exc)
        return ArchitectureSummary(
            summary=(
                f"Architecture summary for {repo_name}. "
                f"Technology stack includes: {', '.join(tech_stack)}."
            ),
            reading_order=file_paths[:5],
            relationships=[],
        )
