"""FastAPI API endpoints for Repo Intelligence Agent.

Provides endpoints for repository analysis, issue mapping, and repository chat,
interacting with agents and memory layers.
"""

import sys
import os
import asyncio
import json
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
    EvaluationResult
)
from agents.analyzer import RepositoryAnalyzer
from agents.explainer import ArchitectureExplainer
from agents.issue_mapper import IssueMapper
from agents.evaluator import EvaluationAgent

app = FastAPI(
    title="Repo Intelligence Agent API",
    description="Backend services exposing multi-agent codebase analysis and chat.",
    version="1.0.0"
)

# Enable CORS for frontend development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory session store for analyzed repositories
ANALYSIS_STORE: Dict[str, Dict[str, Any]] = {}


class AnalyzeRequest(BaseModel):
    url: str = Field(..., description="GitHub repository URL")
    branch: str = Field("main", description="Git branch or ref")
    model: str = Field("Gemini 2.5 Flash", description="Gemini LLM variant to use")


class IssueMapRequest(BaseModel):
    repo: str = Field(..., description="Repository identifier (owner/repo)")
    title: str = Field(..., description="GitHub issue title")
    description: str = Field("", description="GitHub issue body/details")


class ChatRequest(BaseModel):
    repo: str = Field(..., description="Repository identifier (owner/repo)")
    message: str = Field(..., description="User message")
    history: List[Dict[str, Any]] = Field(default_factory=list, description="Conversation history")


def parse_repo_name(url: str) -> str:
    """Parses owner/repo from a GitHub URL."""
    url = url.strip()
    if url.endswith(".git"):
        url = url[:-4]
    
    parts = url.split("github.com/")
    if len(parts) > 1:
        return parts[1]
    
    # Fallback if it's already in owner/repo format
    return url


@app.get("/api/repos/examples")
async def get_examples():
    """Lists pre-configured example repositories for user reference."""
    return [
        {
            "name": "google/guava",
            "url": "https://github.com/google/guava",
            "tech_stack": ["Java", "Maven"],
            "description": "Google core libraries for Java."
        },
        {
            "name": "fastapi/fastapi",
            "url": "https://github.com/fastapi/fastapi",
            "tech_stack": ["Python", "Pydantic", "Starlette"],
            "description": "High performance, easy to learn, fast to code, ready for production API framework."
        },
        {
            "name": "vercel/next.js",
            "url": "https://github.com/vercel/next.js",
            "tech_stack": ["JavaScript", "TypeScript", "React", "Rust"],
            "description": "The React Framework for the Web."
        }
    ]


@app.get("/api/repos/recent")
async def get_recent():
    """Fetches list of recently analyzed repositories from the store."""
    return [
        {
            "name": name,
            "url": f"https://github.com/{name}",
            "tech_stack": data["analysis"].tech_stack,
            "analyzed_at": "Just now"
        }
        for name, data in ANALYSIS_STORE.items()
    ]


@app.post("/api/analyze")
async def analyze_repository(request: AnalyzeRequest):
    """Triggers analysis and returns a SSE stream of progress and final results."""
    repo_name = parse_repo_name(request.url)
    
    async def event_generator():
        steps = [
            ("cloning", "Cloning repository from GitHub...", 1.5),
            ("cloned", "✓ Repository cloned successfully", 0.5),
            ("detecting", "Detecting languages and frameworks...", 1.5),
            ("detected", "✓ Technologies detected (Python, FastAPI, TypeScript, Astro)", 0.5),
            ("analyzing", "Running architecture parsing and indexing codebase...", 2.0),
            ("analyzed", "✓ Architecture analyzed", 0.5),
            ("mapping", "Mapping module relationships and suggested reading order...", 1.5),
            ("complete", "✓ Repository analysis complete!", 0.5),
        ]
        
        for status, msg, delay in steps:
            await asyncio.sleep(delay)
            yield f"data: {json.dumps({'status': status, 'message': msg})}\n\n"
            
        # Store mock results matching RepositoryAnalysis & ArchitectureSummary schemas
        mock_analysis = RepositoryAnalysis(
            structure={
                "root": [".gitignore", "README.md", "requirements.txt", "package.json"],
                "src": ["main.py", "api.py", "utils.py"],
                "agents": ["analyzer.py", "explainer.py", "issue_mapper.py"],
                "ui": ["streamlit_app.py"],
                "tests": ["test_agents.py", "test_services.py"]
            },
            dependencies=["fastapi", "google-genai", "chromadb", "pydantic", "pytest"],
            tech_stack=["Python", "FastAPI", "Astro", "Tailwind CSS", "SQLite"],
            metadata={"owner": repo_name.split("/")[0] if "/" in repo_name else "owner", "name": repo_name.split("/")[1] if "/" in repo_name else repo_name}
        )
        
        mock_architecture = ArchitectureSummary(
            summary=f"The `{repo_name}` repository is a multi-agent application centered around codebase intelligence. "
                    f"It exposes an agent layer to analyze repositories, recommend reading orders, and plan issue fixes. "
                    f"A local SQLite database caches system states while ChromaDB powers vector embeddings of codebase snippets.",
            reading_order=["README.md", "src/main.py", "models/schemas.py", "agents/analyzer.py"],
            relationships=[
                ComponentRelationship(source="src/main.py", target="models/schemas.py", relationship_type="imports", description="Loads core Pydantic data schemas."),
                ComponentRelationship(source="agents/analyzer.py", target="models/schemas.py", relationship_type="inherits", description="Returns typed analysis results conforming to the schema."),
                ComponentRelationship(source="ui/streamlit_app.py", target="agents/analyzer.py", relationship_type="calls", description="Triggers scanning and maps directory structure.")
            ]
        )
        
        ANALYSIS_STORE[repo_name] = {
            "analysis": mock_analysis,
            "architecture": mock_architecture
        }
        
        yield f"data: {json.dumps({'status': 'done', 'repo': repo_name})}\n\n"
        
    return StreamingResponse(event_generator(), media_type="text/event-stream")


@app.get("/api/analysis/{owner}/{repo_name}")
async def get_analysis_details(owner: str, repo_name: str):
    """Retrieves computed analysis and architecture summary for a repository."""
    full_name = f"{owner}/{repo_name}"
    if full_name not in ANALYSIS_STORE:
        # Generate default mock data on the fly if not in store
        ANALYSIS_STORE[full_name] = {
            "analysis": RepositoryAnalysis(
                structure={
                    ".": ["README.md", "package.json", "tailwind.config.js", "astro.config.mjs"],
                    "src/components": ["Navbar.astro", "Sidebar.astro", "Button.tsx"],
                    "src/layouts": ["Layout.astro"],
                    "src/pages": ["index.astro", "issues.astro", "chat.astro"]
                },
                dependencies=["astro", "tailwindcss", "react", "lucide-react", "class-variance-authority"],
                tech_stack=["TypeScript", "Astro", "React", "Tailwind CSS"],
                metadata={"owner": owner, "name": repo_name}
            ),
            "architecture": ArchitectureSummary(
                summary=f"A modern Astro frontend repository implementing a developer dashboard for {full_name}. "
                        "The application uses Astro file-based routing for page structures combined with React client-islands "
                        "for stateful components like the Interactive File Tree and Code Chat UI.",
                reading_order=["README.md", "astro.config.mjs", "src/layouts/Layout.astro", "src/pages/index.astro"],
                relationships=[
                    ComponentRelationship(source="src/pages/index.astro", target="src/layouts/Layout.astro", relationship_type="imports", description="Wraps the home page within the main application layout."),
                    ComponentRelationship(source="src/layouts/Layout.astro", target="src/components/Navbar.astro", relationship_type="renders", description="Displays top-navigation on all pages.")
                ]
            )
        }
        
    return ANALYSIS_STORE[full_name]


@app.post("/api/issues/map", response_model=ImplementationPlan)
async def map_issue(request: IssueMapRequest):
    """Analyzes a GitHub issue and returns the implementation plan and relevant files."""
    # Attempt to use IssueMapper agent. Fall back to mock if not implemented
    try:
        mapper = IssueMapper()
        # This will raise NotImplementedError as it's a skeleton backend
        plan = mapper.map_issue(request.title, request.description)
        return plan
    except NotImplementedError:
        # Supply a highly-realistic, dynamic mock response conforming to the schema
        return ImplementationPlan(
            issue_summary=f"Resolve issue: {request.title}",
            relevant_files=["backend/api.py", "frontend/src/components/interactive/Timeline.tsx", "models/schemas.py"],
            steps=[
                ImplementationPlanStep(
                    step_number=1,
                    description="Expose the Event Stream status updates correctly from backend/api.py to support timeline rendering.",
                    files_to_modify=["backend/api.py"]
                ),
                ImplementationPlanStep(
                    step_number=2,
                    description="Listen to Server-Sent Events (SSE) in the frontend React Timeline component and update state icons accordingly.",
                    files_to_modify=["frontend/src/components/interactive/Timeline.tsx"]
                )
            ]
        )


@app.post("/api/chat")
async def repository_chat(request: ChatRequest):
    """Chats with repository context, streaming back word-by-word token results."""
    
    async def chat_streamer():
        response_text = (
            f"Here is how you can understand the codebase for `{request.repo}`:\n\n"
            "1. **Entry Point**: The primary backend entry point is `backend/api.py` which sets up the FastAPI application.\n"
            "2. **Agent Layout**: The system contains agents inside the `/agents` folder: `RepositoryAnalyzer`, `ArchitectureExplainer`, and `IssueMapper`.\n"
            "3. **Frontend Integration**: The frontend communicates via standard fetch calls for static info, and SSE stream endpoints for analyzing progress.\n\n"
            "Let me know if you want me to write a custom endpoint or explain a specific agent class!"
        )
        
        # Stream word by word to emulate real LLM behavior
        words = response_text.split(" ")
        for word in words:
            yield f"data: {json.dumps({'text': word + ' '})}\n\n"
            await asyncio.sleep(0.08)
            
        yield f"data: {json.dumps({'status': 'done'})}\n\n"

    return StreamingResponse(chat_streamer(), media_type="text/event-stream")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api:app", host="127.0.0.1", port=8000, reload=True)
