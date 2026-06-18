"""Main entry point to run the FastAPI server."""

import uvicorn

def main():
    """Starts the FastAPI backend application."""
    uvicorn.run("backend.api:app", host="127.0.0.1", port=8001, reload=True)

if __name__ == "__main__":
    main()
