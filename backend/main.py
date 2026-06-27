"""Main entry point to run the FastAPI server."""

import uvicorn

# Watch ONLY source dirs. Without this, WatchFiles scans the whole project tree
# (including data/, .venv/, __pycache__/) and triggers a reload whenever a
# cloned repo writes a file — killing in-flight analysis requests.
_RELOAD_DIRS = ["backend", "services", "agents", "memory", "models"]
_RELOAD_EXCLUDES = [
    "data/*",
    "data/**",
    "data/cloned_repos/**",
    "data/vector_store/**",
    "data/graphs/**",
    "__pycache__/**",
    ".cache/**",
    "*.log",
    "tests/**",
]


def main():
    """Starts the FastAPI backend application."""
    from backend.settings import settings

    uvicorn.run(
        "backend.api:app",
        host=settings.host,
        port=settings.port,
        reload=settings.app_env == "development",
        reload_dirs=_RELOAD_DIRS,
        reload_excludes=_RELOAD_EXCLUDES,
    )


if __name__ == "__main__":
    main()
