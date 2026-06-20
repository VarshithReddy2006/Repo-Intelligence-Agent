"""Main entry point to run the FastAPI server."""

import os
import uvicorn

# Watch ONLY source dirs. Without this, WatchFiles scans the whole project tree
# (including data/, .venv/, __pycache__/) and triggers a reload whenever a
# cloned repo writes a file — killing in-flight analysis requests.
_RELOAD_DIRS = ["backend", "services", "agents", "memory", "models"]


def main():
    """Starts the FastAPI backend application."""
    host = os.environ.get("API_SERVER_HOST", "127.0.0.1")
    port = int(os.environ.get("API_SERVER_PORT", "8001"))
    uvicorn.run(
        "backend.api:app",
        host=host,
        port=port,
        reload=True,
        reload_dirs=_RELOAD_DIRS,
    )


if __name__ == "__main__":
    main()
