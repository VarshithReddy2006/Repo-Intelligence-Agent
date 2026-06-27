"""Architecture router.

Endpoints:
  POST /api/architecture/build
  GET  /api/architecture/{owner}/{repo_name}
  GET  /api/architecture/{owner}/{repo_name}/graph
  POST /api/reading-order
  POST /api/impact-analysis
"""

import asyncio
import logging
import os
from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from backend.dependencies import (
    architecture_service,
    graph_service,
    impact_analysis_service,
    reading_order_service,
    symbol_service,
    github_service,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["Architecture"])


# ---------------------------------------------------------------------------
# Request models
# ---------------------------------------------------------------------------


class ArchitectureBuildRequest(BaseModel):
    repo: str = Field(..., description="Repository identifier (owner/repo)")


class ReadingOrderRequest(BaseModel):
    repo: str = Field(..., description="Repository identifier (owner/repo)")


class ImpactAnalysisRequest(BaseModel):
    repo: str = Field(..., description="Repository identifier (owner/repo)")
    issue: str = Field(..., description="Change request or GitHub issue text")


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.post("/architecture/build")
async def build_architecture(request: ArchitectureBuildRequest):
    """Parse the repository, build the dependency graph, and generate architecture metadata."""
    repo_name = request.repo.strip()
    try:
        local_path = github_service.get_local_repo_path(repo_name)
        if not os.path.exists(local_path):
            raise HTTPException(
                status_code=404,
                detail=(
                    f"Repository '{repo_name}' has not been cloned yet. "
                    "Please index or analyse the repository first."
                ),
            )
        result = await asyncio.to_thread(
            architecture_service.build, repo_name, local_path, None, False
        )
        try:
            await asyncio.to_thread(symbol_service.build, repo_name, local_path, None)
        except Exception as sym_exc:
            logger.warning(
                "Symbol index build failed for %s (non-fatal): %s", repo_name, sym_exc
            )
        return {
            "status": result["status"],
            "repo": result["repo"],
            "files_parsed": result["files_parsed"],
            "dependencies_found": result["dependencies_found"],
            "entry_points": result["entry_points"],
        }
    except HTTPException:
        raise
    except Exception as exc:
        logger.error(
            "Architecture build failed for %s: %s", repo_name, exc, exc_info=True
        )
        raise HTTPException(
            status_code=500,
            detail=f"Architecture build failed: {str(exc)}",
        )


@router.get("/architecture/{owner}/{repo_name}")
async def get_architecture_summary(owner: str, repo_name: str):
    """Return the persisted architecture summary for a repository."""
    full_name = f"{owner}/{repo_name}"
    try:
        summary = await asyncio.to_thread(architecture_service.get_summary, full_name)
        if summary is None:
            raise HTTPException(
                status_code=404,
                detail=(
                    f"No architecture summary found for '{full_name}'. "
                    "Please run POST /api/architecture/build first."
                ),
            )
        return summary.model_dump()
    except HTTPException:
        raise
    except Exception as exc:
        logger.error(
            "Failed to retrieve architecture for %s: %s", full_name, exc, exc_info=True
        )
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve architecture: {str(exc)}",
        )


@router.get("/architecture/{owner}/{repo_name}/graph")
async def get_architecture_graph(
    owner: str,
    repo_name: str,
    q: Optional[str] = Query(None),
):
    """Return React Flow compatible dependency graph data for a repository."""
    full_name = f"{owner}/{repo_name}"
    try:
        if not graph_service.graph_exists(full_name):
            raise HTTPException(
                status_code=404,
                detail=(
                    f"No dependency graph found for '{full_name}'. "
                    "Please analyse the repository first."
                ),
            )
        graph_data = await asyncio.to_thread(
            graph_service.get_visualization_graph, full_name, architecture_service, q
        )
        if not graph_data.get("nodes"):
            raise HTTPException(
                status_code=404,
                detail=(
                    f"Dependency graph for '{full_name}' exists but contains no nodes. "
                    "Re-analyse the repository to rebuild the graph with the latest code."
                ),
            )
        return graph_data
    except HTTPException:
        raise
    except Exception as exc:
        logger.error(
            "Failed to retrieve graph for %s: %s", full_name, exc, exc_info=True
        )
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve architecture graph: {str(exc)}",
        )


@router.post("/reading-order")
async def get_reading_order(request: ReadingOrderRequest):
    """Generate the optimal code-reading sequence for a repository."""
    repo_name = request.repo.strip()
    try:
        reading_order = await asyncio.to_thread(
            reading_order_service.generate_reading_order, repo_name
        )
        return reading_order.model_dump()
    except ValueError as val_err:
        raise HTTPException(status_code=404, detail=str(val_err))
    except Exception as exc:
        logger.error("Reading order failed for %s: %s", repo_name, exc, exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Reading order generation failed: {str(exc)}",
        )


@router.post("/impact-analysis")
async def get_impact_analysis(request: ImpactAnalysisRequest):
    """Predict which files and components are affected by a proposed change."""
    repo_name = request.repo.strip()
    issue_text = request.issue.strip()
    try:
        impact_analysis = await asyncio.to_thread(
            impact_analysis_service.analyze_change, repo_name, issue_text
        )
        return impact_analysis.model_dump()
    except ValueError as val_err:
        raise HTTPException(status_code=404, detail=str(val_err))
    except Exception as exc:
        logger.error("Impact analysis failed for %s: %s", repo_name, exc, exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Impact analysis failed: {str(exc)}",
        )
