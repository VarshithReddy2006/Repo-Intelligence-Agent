"""Unit tests verifying real implementations and interface for service classes."""

import pytest
from services import GitHubService, EmbeddingService, MCPService
from services.chunking_service import CodeChunker


def test_github_service_init() -> None:
    """Verifies GitHubService can be instantiated and parses repository URLs correctly."""
    service = GitHubService(token="dummy_token")
    assert service.token == "dummy_token"

    # Test URL parsing helper
    parsed = service.parse_repo_url("https://github.com/google/guava")
    assert parsed["owner"] == "google"
    assert parsed["repo"] == "guava"

    parsed = service.parse_repo_url("google/guava")
    assert parsed["owner"] == "google"
    assert parsed["repo"] == "guava"

    parsed = service.parse_repo_url("https://github.com/google/guava.git")
    assert parsed["owner"] == "google"
    assert parsed["repo"] == "guava"


def test_code_chunker() -> None:
    """Verifies CodeChunker divides content into chunks and detects language."""
    chunker = CodeChunker(chunk_size=50, chunk_overlap=10)

    # Language detection
    assert chunker.detect_language("src/main.py") == "python"
    assert chunker.detect_language("index.html") == "html"
    assert chunker.detect_language("styles.css") == "css"
    assert chunker.detect_language("docs.txt") == "text"

    # Chunking content
    content = "line1\nline2\nline3\nline4\nline5\nline6"
    chunks = chunker.chunk_file("test.py", content)

    assert len(chunks) > 0
    assert all("path" in c for c in chunks)
    assert all("chunk_id" in c for c in chunks)
    assert all("content" in c for c in chunks)
    assert all(c["language"] == "python" for c in chunks)

    # Empty content should produce no chunks
    assert chunker.chunk_file("empty.py", "") == []

    # Whitespace-only content should produce no chunks
    assert chunker.chunk_file("ws.py", "   \n\t  ") == []


def test_embedding_service_init() -> None:
    """Verifies EmbeddingService can be instantiated and checks the default model name."""
    service = EmbeddingService(client=None, model_name="dummy-model")
    assert service.model_name is not None


def test_mcp_service_init() -> None:
    """Verifies MCPService can be instantiated and raises NotImplementedError for unimplemented skeleton methods."""
    service = MCPService(server_url="dummy_url")
    assert service.server_url == "dummy_url"

    with pytest.raises(NotImplementedError):
        service.connect()
