"""ChromaDB store module for vector embeddings.

Manages code chunk indexing, file storage, and semantic searches.
"""

import os
import logging
import time
import chromadb
from typing import Dict, List, Any, Optional

logger = logging.getLogger(__name__)


class ChromaStore:
    """Interface to interact with ChromaDB local client vector database."""

    def __init__(self, persist_directory: str) -> None:
        """Initializes the ChromaStore connection.

        Args:
            persist_directory: Path to the directory where ChromaDB stores its data.
        """
        self.persist_directory = persist_directory
        # Ensure the directory exists
        os.makedirs(self.persist_directory, exist_ok=True)
        self.client = chromadb.PersistentClient(path=self.persist_directory)
        # We create a single collection to store code chunks.
        self.collection = self.client.get_or_create_collection(name="repository_chunks")

    def add_code_chunks(
        self,
        file_path: str,
        chunks: List[str],
        embeddings: List[List[float]],
        metadata: List[Dict[str, Any]],
    ) -> None:
        """Adds code chunks with their precomputed embeddings and metadata to ChromaDB.

        Args:
            file_path: Relative or absolute path of the file being indexed.
            chunks: A list of text/code blocks.
            embeddings: Parallel list of float-vector embeddings.
            metadata: Parallel list of dictionaries containing chunk details.
        """
        if not chunks:
            return

        ids = [f"{file_path}_{i}" for i in range(len(chunks))]
        
        # Clean metadata to contain only allowed types (str, int, float, bool)
        cleaned_metadata = []
        for meta in metadata:
            cleaned = {}
            for k, v in meta.items():
                if isinstance(v, (str, int, float, bool)):
                    cleaned[k] = v
                else:
                    cleaned[k] = str(v)
            cleaned_metadata.append(cleaned)

        self.collection.add(
            ids=ids,
            documents=chunks,
            embeddings=embeddings,
            metadatas=cleaned_metadata
        )

    def search_similar(
        self,
        query_embedding: List[float],
        limit: int = 5,
        where_filter: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """Performs a vector search to find code chunks similar to the query embedding.

        Args:
            query_embedding: The float vector of the query phrase/code.
            limit: Maximum number of search results.
            where_filter: Key-value dictionary to filter metadata matches.

        Returns:
            A list of dictionary objects representing the matched chunks and their metadata.
        """
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=limit,
            where=where_filter
        )

        formatted_results = []
        if results and "documents" in results and results["documents"]:
            docs = results["documents"][0]
            metas = results["metadatas"][0] if "metadatas" in results and results["metadatas"] else [{}] * len(docs)
            ids = results["ids"][0] if "ids" in results and results["ids"] else [""] * len(docs)
            distances = results["distances"][0] if "distances" in results and results["distances"] else [0.0] * len(docs)

            for doc, meta, idx, dist in zip(docs, metas, ids, distances):
                formatted_results.append({
                    "id": idx,
                    "content": doc,
                    "metadata": meta,
                    "distance": dist
                })

        return formatted_results

    def clear_database(self) -> None:
        """Deletes all collections and clears current vector index storage."""
        try:
            self.client.delete_collection(name="repository_chunks")
        except Exception as e:
            logger.debug(f"Failed to delete collection during clear: {e}")
            pass
        self.collection = self.client.get_or_create_collection(name="repository_chunks")

    def index_repository(self, repo_name: str, chunks: List[Dict[str, Any]], embeddings: List[List[float]]) -> None:
        """Indexes a full list of repository chunks with their embeddings in ChromaDB.

        Args:
            repo_name: The repository identifier (owner/repo).
            chunks: A list of chunk dictionary structures.
            embeddings: Parallel list of float-vector embeddings.
        """
        if not chunks:
            return

        # Filter out empty / whitespace-only chunks to avoid indexing junk.
        filtered_chunks: List[Dict[str, Any]] = []
        filtered_indices: List[int] = []
        for idx, chunk in enumerate(chunks):
            content = chunk.get("content", "")
            if isinstance(content, str) and content.strip():
                filtered_chunks.append(chunk)
                filtered_indices.append(idx)

        if not filtered_chunks:
            # Still ensure the repo index is clean.
            self.delete_repository(repo_name)
            return

        logger.info(
            "[PIPELINE:%s] CHROMA index_repository start raw_chunks=%d filtered_chunks=%d embeddings_provided=%s",
            repo_name,
            len(chunks),
            len(filtered_chunks),
            ("yes" if embeddings is not None else "no"),
        )

        # Clean existing entries for this repository to allow clean re-indexing
        t0 = time.perf_counter()
        self.delete_repository(repo_name)
        logger.info(
            "[PIPELINE:%s] CHROMA delete_repository elapsed=%.2fs",
            repo_name,
            time.perf_counter() - t0,
        )

        if embeddings is not None and filtered_indices:
            if len(embeddings) < (max(filtered_indices) + 1):
                raise ValueError(
                    f"Embeddings length ({len(embeddings)}) does not match chunk indices "
                    f"(max index {max(filtered_indices)})."
                )

            filtered_embeddings = [embeddings[i] for i in filtered_indices]
        else:
            # If embeddings were not provided properly, raise to avoid silent corruption.
            raise ValueError("Embeddings must be provided and aligned with chunks.")

        ids: List[str] = []
        documents: List[str] = []
        metadatas: List[Dict[str, Any]] = []

        for out_idx, chunk in enumerate(filtered_chunks):
            path = chunk.get("path", "")
            chunk_id = chunk.get("chunk_id", out_idx)
            unique_id = f"{repo_name}_{path}_{chunk_id}".replace("/", "_").replace(".", "_")

            ids.append(unique_id)
            documents.append(chunk.get("content", ""))

            metadatas.append(
                {
                    "repo_name": repo_name,
                    "file_path": path,
                    "chunk_id": chunk_id,
                    "language": chunk.get("language", "text"),
                }
            )

        # Batch additions (Chroma recommends keeping batches under 2000 items)
        batch_size = 2000
        logger.info(
            "[PIPELINE:%s] CHROMA add loop start total_ids=%d batch_size=%d",
            repo_name,
            len(ids),
            batch_size,
        )
        t_total = time.perf_counter()
        batch_count = 0
        for i in range(0, len(ids), batch_size):
            batch_count += 1
            bi = i // batch_size
            t_batch = time.perf_counter()
            self.collection.add(
                ids=ids[i:i + batch_size],
                documents=documents[i:i + batch_size],
                embeddings=filtered_embeddings[i:i + batch_size],
                metadatas=metadatas[i:i + batch_size],
            )
            logger.info(
                "[PIPELINE:%s] CHROMA add batch %d/%d elapsed=%.2fs batch_items=%d",
                repo_name,
                bi + 1,
                ((len(ids) + batch_size - 1) // batch_size),
                time.perf_counter() - t_batch,
                min(batch_size, len(ids) - i),
            )
        logger.info(
            "[PIPELINE:%s] CHROMA add loop completed batches=%d elapsed=%.2fs total_ids=%d",
            repo_name,
            batch_count,
            time.perf_counter() - t_total,
            len(ids),
        )

        logger.info(f"Successfully indexed {len(ids)} chunks for repository {repo_name}.")

    def search_repository(self, repo_name: str, query_embedding: List[float], limit: int = 5) -> List[Dict[str, Any]]:
        """Searches for chunks in a specific repository similar to the query embedding.

        Args:
            repo_name: The repository identifier.
            query_embedding: The search phrase embedding vector.
            limit: Maximum number of results.

        Returns:
            A list of dictionary records containing content and file_path metadata.
        """
        return self.search_similar(
            query_embedding=query_embedding,
            limit=limit,
            where_filter={"repo_name": repo_name}
        )

    def delete_repository(self, repo_name: str) -> None:
        """Deletes all chunks associated with a repository name.

        Args:
            repo_name: The repository identifier.
        """
        try:
            self.collection.delete(where={"repo_name": repo_name})
            logger.info(f"Deleted vector index for repository: {repo_name}")
        except Exception as e:
            logger.debug(f"Repository {repo_name} could not be deleted from Chroma: {e}")
            pass
