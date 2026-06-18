"""Issue Retrieval Service — Phase 2.

Encapsulates retrieving relevant code chunks and context for a specific issue,
leveraging ChromaStore and EmbeddingService.
"""

import logging
from typing import List, Dict, Any, Optional

from memory.chroma_store import ChromaStore
from services.embedding_service import EmbeddingService

logger = logging.getLogger(__name__)


class IssueRetrievalService:
    """Service that queries the repository index for chunks relevant to an issue."""

    def __init__(
        self,
        embedding_service: EmbeddingService,
        chroma_store: ChromaStore,
    ) -> None:
        """Initializes the IssueRetrievalService.

        Args:
            embedding_service: Pre-configured EmbeddingService instance.
            chroma_store:      Pre-configured ChromaStore instance.
        """
        self.embedding_service = embedding_service
        self.chroma_store = chroma_store

    def retrieve_issue_context(
        self,
        repo_name: str,
        issue_text: str,
        limit: int = 20,
    ) -> List[Dict[str, Any]]:
        """Finds code chunks in the repository related to the issue query.

        Args:
            repo_name:  Repository identifier (owner/repo).
            issue_text: Text of the issue / search query.
            limit:      Max number of chunks to return.

        Returns:
            A list of dictionary chunks with content and metadata.
        """
        try:
            query_embedding = self.embedding_service.generate_embedding(issue_text)
            return self.chroma_store.search_repository(
                repo_name=repo_name,
                query_embedding=query_embedding,
                limit=limit,
            )
        except Exception as e:
            logger.error("Failed to retrieve issue context chunks: %s", e)
            return []
