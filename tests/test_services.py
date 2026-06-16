"""Unit tests verifying import and initialization interface for service classes."""

import pytest
from services import GitHubService, EmbeddingService, MCPService


def test_github_service_init() -> None:
    """Verifies GitHubService can be instantiated and raises NotImplementedError for unimplemented methods."""
    service = GitHubService(token="dummy_token")
    assert service.token == "dummy_token"

    with pytest.raises(NotImplementedError):
        service.fetch_repository_files("owner/repo")

    with pytest.raises(NotImplementedError):
        service.fetch_file_content("owner/repo", "file.py")

    with pytest.raises(NotImplementedError):
        service.fetch_issues("owner/repo")


def test_embedding_service_init() -> None:
    """Verifies EmbeddingService can be instantiated and raises NotImplementedError for unimplemented methods."""
    # Pass a dummy client or none to prevent actual API connection attempts during testing
    service = EmbeddingService(client=None)
    assert service.model_name == "text-embedding-004"

    with pytest.raises(NotImplementedError):
        service.generate_embedding("dummy text")

    with pytest.raises(NotImplementedError):
        service.generate_embeddings_batch(["dummy text"])


def test_mcp_service_init() -> None:
    """Verifies MCPService can be instantiated and raises NotImplementedError for unimplemented methods."""
    service = MCPService(server_url="dummy_url")
    assert service.server_url == "dummy_url"

    with pytest.raises(NotImplementedError):
        service.connect()

    with pytest.raises(NotImplementedError):
        service.list_tools()

    with pytest.raises(NotImplementedError):
        service.execute_tool("dummy_tool", {})

    with pytest.raises(NotImplementedError):
        service.disconnect()
