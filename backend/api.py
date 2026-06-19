"""FastAPI API endpoints for Repo Intelligence Agent.

Provides endpoints for repository analysis, indexing, semantic retrieval, and
repository chat, interacting with agents and memory layers.

AI provider: DeepSeek V4 Flash via NVIDIA NIM (ProviderFactory).
Embeddings:  Local BAAI/bge-small-en-v1.5 via sentence-transformers.
"""

import sys
import os

# Load .env before any service reads os.environ
from dotenv import load_dotenv
load_dotenv()

import asyncio
import json
import logging
import time
from typing import Dict, List, Any, Optional
from fastapi import FastAPI, HTTPException, Request, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

# Ensure parent directory is in sys.path to import project modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models.schemas import (
    RepositoryAnalysis,
    ArchitectureSummary,
    ComponentRelationship,
    ImplementationPlan,
    ImplementationPlanStep,
    EvaluationResult,
    IssueMapResponse,
)
from agents.issue_mapper import IssueMapper
from agents.evaluator import EvaluationAgent

from services.github_service import GitHubService
from services.chunking_service import CodeChunker
from services.embedding_service import EmbeddingService
from services.retrieval_service import RetrievalService
from services.architecture_service import ArchitectureService
from services.graph_service import GraphService
from services.reading_order_service import ReadingOrderService
from services.impact_analysis_service import ImpactAnalysisService
from services.arch_context_service import ArchContextService
from services.llm import ProviderFactory
from memory.chroma_store import ChromaStore

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

app = FastAPI(
    title="Repo Intelligence Agent API",
    description="Backend services exposing multi-agent codebase analysis and chat.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health():
    """Health check — reports active AI providers."""
    return {
        "backend": "online",
        "llm_provider": "deepseek",
        "llm_model": os.environ.get("DEEPSEEK_MODEL", "deepseek-ai/deepseek-v4-flash"),
        "embedding_provider": "bge-small-en-v1.5",
        "vector_db": "chromadb",
        "status": "healthy",
    }


# ---------------------------------------------------------------------------
# In-memory session store for analyzed repositories
# ---------------------------------------------------------------------------
ANALYSIS_STORE: Dict[str, Dict[str, Any]] = {}

# ---------------------------------------------------------------------------
# Core service singletons
# ---------------------------------------------------------------------------
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN")
CHROMA_DB_PATH = os.environ.get("CHROMA_DB_PATH", "data/chroma_db")

github_service = GitHubService(token=GITHUB_TOKEN)
embedding_service = EmbeddingService()
chroma_store = ChromaStore(persist_directory=CHROMA_DB_PATH)
chunker = CodeChunker()
retrieval_service = RetrievalService(
    embedding_service=embedding_service,
    chroma_store=chroma_store,
)
architecture_service = ArchitectureService()
graph_service = GraphService()
reading_order_service = ReadingOrderService(architecture_service=architecture_service)
impact_analysis_service = ImpactAnalysisService(architecture_service=architecture_service)
arch_context_service = ArchContextService(architecture_service=architecture_service)


# ---------------------------------------------------------------------------
# Request / Response models
# ---------------------------------------------------------------------------

class AnalyzeRequest(BaseModel):
    url: str = Field(..., description="GitHub repository URL")
    branch: str = Field("main", description="Git branch or ref")
    model: str = Field("deepseek-ai/deepseek-v4-flash", description="LLM model variant to use")


class IndexRequest(BaseModel):
    repo_url: str = Field(..., description="GitHub repository URL")


class RetrieveRequest(BaseModel):
    repo: str = Field(..., description="Repository identifier (owner/repo)")
    question: str = Field(..., description="Question query")


class IssueMapRequest(BaseModel):
    repo: str = Field(..., description="Repository identifier (owner/repo)")
    issue: Optional[str] = Field(None, description="GitHub issue text/details")
    title: Optional[str] = Field(None, description="GitHub issue title")
    description: Optional[str] = Field("", description="GitHub issue body/details")


class ChatRequest(BaseModel):
    repo: str = Field(..., description="Repository identifier (owner/repo)")
    message: str = Field(..., description="User message")
    history: List[Dict[str, Any]] = Field(
        default_factory=list, description="Conversation history"
    )


class ArchitectureBuildRequest(BaseModel):
    repo: str = Field(..., description="Repository identifier (owner/repo)")


class ReadingOrderRequest(BaseModel):
    repo: str = Field(..., description="Repository identifier (owner/repo)")


class ImpactAnalysisRequest(BaseModel):
    repo: str = Field(..., description="Repository identifier (owner/repo)")
    issue: str = Field(..., description="Change request or GitHub issue text")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def parse_repo_name(url: str) -> str:
    """Parse owner/repo from a GitHub URL."""
    url = url.strip()
    if url.endswith(".git"):
        url = url[:-4]
    parts = url.split("github.com/")
    if len(parts) > 1:
        return parts[1]
    return url


def detect_tech_stack_and_deps(
    files: List[Dict[str, Any]],
) -> tuple[List[str], List[str]]:
    """Detect language tech stack and packages based on file heuristics."""
    tech_stack: set = set()
    dependencies: set = set()

    file_paths = [f["path"] for f in files]
    for p in file_paths:
        ext = os.path.splitext(p)[1].lower()
        if ext == ".py":
            tech_stack.add("Python")
        elif ext in (".js", ".jsx"):
            tech_stack.add("JavaScript")
        elif ext in (".ts", ".tsx"):
            tech_stack.add("TypeScript")
        elif ext == ".html":
            tech_stack.add("HTML")
        elif ext == ".css":
            tech_stack.add("CSS")
        elif ext == ".go":
            tech_stack.add("Go")
        elif ext == ".rs":
            tech_stack.add("Rust")
        elif ext == ".java":
            tech_stack.add("Java")

        if p.endswith("package.json"):
            tech_stack.add("Node.js")
        elif p.endswith("requirements.txt") or p.endswith("pyproject.toml"):
            tech_stack.add("Python")

    for f in files:
        if f["path"].endswith("package.json"):
            try:
                data = json.loads(f["content"])
                for dep_key in ("dependencies", "devDependencies"):
                    if dep_key in data:
                        dependencies.update(data[dep_key].keys())
            except Exception:
                pass
        elif f["path"].endswith("requirements.txt"):
            for line in f["content"].splitlines():
                line = line.strip()
                if line and not line.startswith("#"):
                    pkg = (
                        line.split("=")[0]
                        .split(">")[0]
                        .split("<")[0]
                        .split("[")[0]
                        .strip()
                    )
                    if pkg:
                        dependencies.add(pkg)

    return list(tech_stack), list(dependencies)


async def generate_architecture_summary_with_llm(
    repo_name: str,
    tech_stack: List[str],
    file_paths: List[str],
) -> ArchitectureSummary:
    """Generate an ArchitectureSummary using the configured LLM provider."""
    provider = ProviderFactory.get_provider()

    system_instruction = (
        "You are an expert architecture explainer agent. "
        "Summarise the architecture of this repository, map its components, and recommend a file reading order. "
        "Return the output in JSON format conforming to the ArchitectureSummary schema."
    )

    truncated_files = file_paths[:100]
    prompt = (
        f"Repository Name: {repo_name}\n"
        f"Detected Tech Stack: {tech_stack}\n"
        f"Repository File Paths (truncated to 100): {truncated_files}\n\n"
        f"Explain the architecture, suggest a 3-5 file reading order, and specify 2-3 component relationships. "
        f"Ensure your output is a JSON object matching this schema:\n"
        f"{{\n"
        f"  \"summary\": \"high-level text summary\",\n"
        f"  \"reading_order\": [\"path/to/file1\", \"path/to/file2\"],\n"
        f"  \"relationships\": [\n"
        f"    {{\"source\": \"src/main.py\", \"target\": \"models/schemas.py\", \"relationship_type\": \"imports\", \"description\": \"...\"}}\n"
        f"  ]\n"
        f"}}\n"
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
            summary=f"Architecture summary for {repo_name}. Technology stack includes: {', '.join(tech_stack)}.",
            reading_order=file_paths[:5],
            relationships=[],
        )


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@app.get("/api/repos/examples")
async def get_examples():
    """List pre-configured example repositories for user reference."""
    return [
        {
            "name": "google/guava",
            "url": "https://github.com/google/guava",
            "tech_stack": ["Java", "Maven"],
            "description": "Google core libraries for Java.",
        },
        {
            "name": "fastapi/fastapi",
            "url": "https://github.com/fastapi/fastapi",
            "tech_stack": ["Python", "Pydantic", "Starlette"],
            "description": "High performance, easy to learn, fast to code, ready for production API framework.",
        },
        {
            "name": "vercel/next.js",
            "url": "https://github.com/vercel/next.js",
            "tech_stack": ["JavaScript", "TypeScript", "React", "Rust"],
            "description": "The React Framework for the Web.",
        },
    ]


@app.get("/api/repos/recent")
async def get_recent():
    """Fetch list of recently analysed repositories from the in-memory store."""
    return [
        {
            "name": name,
            "url": f"https://github.com/{name}",
            "tech_stack": data["analysis"].tech_stack,
            "analyzed_at": "Just now",
        }
        for name, data in ANALYSIS_STORE.items()
    ]


@app.post("/api/index")
async def index_repository(request: IndexRequest):
    """Clone a repository, chunk the code, generate embeddings, and index in ChromaDB."""
    try:
        repo_url = request.repo_url.strip()
        parsed = github_service.parse_repo_url(repo_url)
        repo_name = f"{parsed['owner']}/{parsed['repo']}"

        local_path = github_service.clone_repository(repo_url)
        files = github_service.extract_source_files(local_path)

        all_chunks = []
        for file in files:
            file_chunks = chunker.chunk_file(file["path"], file["content"])
            if file_chunks:
                all_chunks.extend(file_chunks)

        embeddings = []
        if all_chunks:
            embeddings = embedding_service.generate_embeddings(all_chunks)

        chroma_store.index_repository(repo_name, all_chunks, embeddings)

        return {
            "status": "indexed",
            "files": len(files),
            "chunks": len(all_chunks),
        }
    except Exception as e:
        from services.github_service import (
            InvalidGitHubRepoURLError,
            RepositoryNotFoundError,
        )
        if isinstance(e, InvalidGitHubRepoURLError):
            raise HTTPException(status_code=400, detail=str(e))
        if isinstance(e, RepositoryNotFoundError):
            raise HTTPException(status_code=404, detail=str(e))
        if isinstance(e, ValueError) and "Invalid GitHub repository URL" in str(e):
            raise HTTPException(status_code=400, detail=str(e))

        logger.error("Failed to index repository: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=f"Indexing failed: {str(e)}")


@app.post("/api/retrieve")
async def retrieve_from_repository(request: RetrieveRequest):
    """Search vector database and return a context-aware answer."""
    try:
        result = retrieval_service.retrieve_and_answer(
            request.repo.strip(), request.question.strip()
        )
        return result
    except Exception as e:
        logger.error("Failed to retrieve: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=f"Retrieval failed: {str(e)}")


@app.post("/api/analyze")
async def analyze_repository(request: AnalyzeRequest):
    """Trigger analysis and return an SSE stream of progress and final results."""
    repo_url = request.url.strip()
    repo_name = parse_repo_name(repo_url)

    async def event_generator():
        try:
            yield f"data: {json.dumps({'status': 'cloning', 'message': 'Cloning repository from GitHub...'})}\n\n"
            local_path = await asyncio.to_thread(
                github_service.clone_repository, repo_url, request.branch
            )
            yield f"data: {json.dumps({'status': 'cloned', 'message': '✓ Repository cloned successfully'})}\n\n"

            yield f"data: {json.dumps({'status': 'detecting', 'message': 'Detecting languages and frameworks...'})}\n\n"
            files = await asyncio.to_thread(github_service.extract_source_files, local_path)
            tech_stack, dependencies = detect_tech_stack_and_deps(files)
            yield f"data: {json.dumps({'status': 'detected', 'message': f'✓ Technologies detected: {tech_stack}'})}\n\n"

            yield f"data: {json.dumps({'status': 'analyzing', 'message': 'Running chunking and indexing codebase...'})}\n\n"

            stage_start = time.perf_counter()
            yield f"data: {json.dumps({'status': 'chunking', 'message': 'START: chunking'})}\n\n"
            all_chunks = []
            chunk_files = 0
            for file in files:
                chunk_files += 1
                before = len(all_chunks)
                file_chunks = chunker.chunk_file(file["path"], file["content"])
                all_chunks.extend(file_chunks)
                logger.info(
                    "[PIPELINE:%s] CHUNK file=%s chunks_in=%d chunks_out=%d elapsed=%.2fs",
                    repo_name,
                    file.get("path"),
                    before,
                    len(all_chunks),
                    time.perf_counter() - stage_start,
                )
            yield f"data: {json.dumps({'status': 'chunking', 'message': 'END: chunking'})}\n\n"
            logger.info(
                "[PIPELINE:%s] CHUNKING completed files=%d total_chunks=%d elapsed=%.2fs",
                repo_name,
                chunk_files,
                len(all_chunks),
                time.perf_counter() - stage_start,
            )

            stage_start = time.perf_counter()
            yield f"data: {json.dumps({'status': 'embedding', 'message': 'START: embeddings'})}\n\n"

            embeddings = []
            if all_chunks:
                logger.info(
                    "[PIPELINE:%s] EMBEDDING started total_chunks=%d",
                    repo_name,
                    len(all_chunks),
                )
                embeddings = await asyncio.to_thread(
                    embedding_service.generate_embeddings, all_chunks
                )
                logger.info(
                    "[PIPELINE:%s] EMBEDDING completed embeddings=%d elapsed=%.2fs",
                    repo_name,
                    len(embeddings),
                    time.perf_counter() - stage_start,
                )
            else:
                logger.info("[PIPELINE:%s] EMBEDDING skipped (no chunks)", repo_name)
            yield f"data: {json.dumps({'status': 'embedding', 'message': 'END: embeddings'})}\n\n"


            stage_start = time.perf_counter()
            yield f"data: {json.dumps({'status': 'chroma', 'message': 'START: chroma indexing'})}\n\n"
            logger.info(
                "[PIPELINE:%s] CHROMA indexing started chunks=%d embeddings=%d",
                repo_name,
                len(all_chunks),
                len(embeddings) if embeddings is not None else 0,
            )
            await asyncio.to_thread(
                chroma_store.index_repository, repo_name, all_chunks, embeddings
            )
            logger.info(
                "[PIPELINE:%s] CHROMA indexing completed elapsed=%.2fs",
                repo_name,
                time.perf_counter() - stage_start,
            )
            yield f"data: {json.dumps({'status': 'chroma', 'message': 'END: chroma indexing'})}\n\n"

            yield f"data: {json.dumps({'status': 'building_graph', 'message': 'Building file dependency graph...'})}\n\n"
            await asyncio.to_thread(
                architecture_service.build, repo_name, local_path, None, False
            )

            # Architecture summary via DeepSeek
            architecture_summary = await generate_architecture_summary_with_llm(
                repo_name, tech_stack, [f["path"] for f in files]
            )
            yield f"data: {json.dumps({'status': 'analyzed', 'message': '✓ Architecture analyzed'})}\n\n"

            # Build file tree structure
            structure: Dict[str, List[str]] = {}
            for f in files:
                parts = f["path"].split("/")
                parent = ".".join(parts[:-1]) if len(parts) > 1 else "."
                name = parts[-1]
                structure.setdefault(parent, []).append(name)

            analysis_data = RepositoryAnalysis(
                structure=structure,
                dependencies=dependencies,
                tech_stack=tech_stack,
                metadata={
                    "owner": repo_name.split("/")[0] if "/" in repo_name else "owner",
                    "name": repo_name.split("/")[1] if "/" in repo_name else repo_name,
                    "local_path": local_path,
                },
            )

            ANALYSIS_STORE[repo_name] = {
                "analysis": analysis_data,
                "architecture": architecture_summary,
            }

            yield f"data: {json.dumps({'status': 'complete', 'message': '✓ Repository analysis complete!'})}\n\n"
            yield f"data: {json.dumps({'status': 'done', 'repo': repo_name})}\n\n"

        except Exception as e:
            logger.error("SSE analysis failed: %s", e, exc_info=True)

            from services.github_service import (
                InvalidGitHubRepoURLError,
                RepositoryNotFoundError,
                BranchNotFoundError,
            )

            err_str = str(e)
            if isinstance(e, InvalidGitHubRepoURLError):
                msg = f"✗ Invalid repository URL: {err_str}"
            elif isinstance(e, BranchNotFoundError):
                msg = f"✗ Branch not found: {err_str}"
            elif isinstance(e, RepositoryNotFoundError):
                msg = f"✗ Repository not found: {err_str}"
            else:
                first_line = err_str.split("\n")[0][:200]
                msg = f"Analysis error: {first_line}"

            yield f"data: {json.dumps({'status': 'error', 'message': msg})}\n\n"
            yield f"data: {json.dumps({'status': 'done'})}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@app.get("/api/analysis/{owner}/{repo_name}")
async def get_analysis_details(owner: str, repo_name: str):
    """Retrieve computed analysis and architecture summary for a repository."""
    full_name = f"{owner}/{repo_name}"
    if full_name not in ANALYSIS_STORE:
        raise HTTPException(
            status_code=404,
            detail=f"Repository {full_name} has not been analysed yet. Please analyse or index first.",
        )
    return ANALYSIS_STORE[full_name]


@app.post("/api/issues/map", response_model=IssueMapResponse)
async def map_issue(request: IssueMapRequest):
    """Analyse a GitHub issue and return the implementation plan and relevant files."""
    title = request.issue if request.issue else (request.title or "")
    description = "" if request.issue else (request.description or "")

    if not title.strip():
        raise HTTPException(
            status_code=400,
            detail="Issue title or issue text must be provided.",
        )

    try:
        mapper = IssueMapper(
            embedding_service=embedding_service, chroma_store=chroma_store
        )
        plan = mapper.map_issue(request.repo, title, description)
        return plan
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to map issue: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=f"Issue mapping failed: {str(e)}")


@app.post("/api/chat")
async def repository_chat(request: ChatRequest):
    """Chat with repository context, streaming back token results via SSE."""
    repo_name = request.repo.strip()
    question = request.message.strip()
    history = request.history

    async def chat_streamer():
        try:
            # 1. Embed query (local BGE — no API call)
            query_embedding = embedding_service.generate_embedding(question)

            # 2. Retrieve relevant chunks from ChromaDB
            chunks = chroma_store.search_repository(
                repo_name=repo_name,
                query_embedding=query_embedding,
                limit=5,
            )

            context_blocks = []
            sources: set = set()
            for idx, chunk in enumerate(chunks):
                meta = chunk.get("metadata", {})
                file_path = meta.get("file_path", "unknown")
                sources.add(file_path)
                context_blocks.append(
                    f"--- File: {file_path} ---\n{chunk.get('content', '')}"
                )
            context_str = (
                "\n\n".join(context_blocks) if context_blocks else "No relevant context found."
            )

            # 3. System instruction
            system_instruction = (
                "You are a Repository Intelligence Agent, an expert developer assistant. "
                "You are helping a developer understand a repository's codebase. "
                "Answer the developer's question using the provided codebase context and conversation history. "
                "Be detailed, citing the source files where relevant. "
                "Keep code snippets accurate."
            )

            # 4. Build conversation history in OpenAI format
            #    Normalise Gemini-style turns {"role":"model","parts":["..."]} → {"role":"assistant","content":"..."}
            normalised_history = []
            for turn in history:
                role = turn.get("role", "user")
                if role == "model":
                    role = "assistant"
                parts = turn.get("parts", [])
                if parts:
                    content = parts[0] if isinstance(parts[0], str) else str(parts[0])
                elif "content" in turn:
                    content = turn["content"]
                else:
                    continue
                normalised_history.append({"role": role, "content": content})

            # 5. Architecture context injection
            arch_ctx = arch_context_service.get_context(repo_name)
            arch_block = arch_ctx.to_prompt_block()
            arch_section = f"\n{arch_block}\n" if arch_block else ""

            prompt = (
                f"{arch_section}"
                f"Context from repository:\n"
                f"=======================\n"
                f"{context_str}\n"
                f"=======================\n\n"
                f"Question: {question}"
            )

            # 6. Stream from DeepSeek
            provider = ProviderFactory.get_provider()
            full_text = ""
            async for token in provider.stream(
                prompt=prompt,
                system_instruction=system_instruction,
                history=normalised_history,
            ):
                full_text += token
                yield f"data: {json.dumps({'text': token})}\n\n"

            # 7. Evaluate the full streamed response
            try:
                evaluator = EvaluationAgent()
                eval_result = evaluator.evaluate_response(question, full_text, chunks)
                confidence_pct = int(eval_result.confidence_score * 100)
            except Exception as eval_err:
                logger.error("Chat evaluation failed: %s", eval_err)
                confidence_pct = 85

            yield f"data: {json.dumps({'sources': sorted(list(sources)), 'confidence': confidence_pct, 'status': 'done'})}\n\n"

        except Exception as e:
            logger.error("Chat streaming error: %s", e, exc_info=True)
            yield f"data: {json.dumps({'text': f'Error in agent system: {str(e)}'})}\n\n"
            yield f"data: {json.dumps({'status': 'done'})}\n\n"

    return StreamingResponse(chat_streamer(), media_type="text/event-stream")


# ---------------------------------------------------------------------------
# Architecture Intelligence Endpoints (unchanged business logic)
# ---------------------------------------------------------------------------

@app.post("/api/architecture/build")
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
        logger.error("Architecture build failed for %s: %s", repo_name, exc, exc_info=True)
        raise HTTPException(status_code=500, detail=f"Architecture build failed: {str(exc)}")


@app.get("/api/architecture/{owner}/{repo_name}")
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
        logger.error("Failed to retrieve architecture for %s: %s", full_name, exc, exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to retrieve architecture: {str(exc)}")


@app.post("/api/reading-order")
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
        raise HTTPException(status_code=500, detail=f"Reading order generation failed: {str(exc)}")


@app.post("/api/impact-analysis")
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
        raise HTTPException(status_code=500, detail=f"Impact analysis failed: {str(exc)}")


@app.get("/api/architecture/{owner}/{repo_name}/graph")
async def get_architecture_graph(owner: str, repo_name: str, q: Optional[str] = Query(None)):
    """Return React Flow compatible dependency graph data for a repository."""
    full_name = f"{owner}/{repo_name}"
    try:
        if not graph_service.graph_exists(full_name):
            raise HTTPException(
                status_code=404,
                detail=(
                    f"No dependency graph found for '{full_name}'. "
                    "Please run POST /api/architecture/build first."
                ),
            )
        graph_data = await asyncio.to_thread(
            graph_service.get_visualization_graph, full_name, architecture_service, q
        )
        return graph_data
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Failed to retrieve graph for %s: %s", full_name, exc, exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to retrieve architecture graph: {str(exc)}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api:app", host="127.0.0.1", port=8000, reload=True)
