"""In-memory analysis caching layer (PH2-002)."""

from __future__ import annotations

import logging
import time
from typing import Any, Dict, Optional, Tuple

import threading

logger = logging.getLogger(__name__)


class CacheEntry:
    """A single entry in the analysis cache."""

    def __init__(self, value: Any, schema_version: int) -> None:
        self.value = value
        self.schema_version = schema_version
        self.created_at = time.time()
        self.last_accessed = self.created_at


class AnalysisCache:
    """Shared in-memory cache for parsed AST data, graphs, and summaries."""

    def __init__(self) -> None:
        # Cache map: (repo_name, key, subkey) -> CacheEntry
        self._cache: Dict[Tuple[str, str, Optional[str]], CacheEntry] = {}
        self.hits: Dict[str, int] = {}
        self.misses: Dict[str, int] = {}
        self._lock = threading.RLock()

    def get(
        self,
        repo_name: str,
        key: str,
        schema_version: int,
        subkey: Optional[str] = None,
    ) -> Optional[Any]:
        """Retrieve a cached object if valid and matches the schema version."""
        with self._lock:
            cache_key = (repo_name, key, subkey)
            entry = self._cache.get(cache_key)
            stat_key = f"{key}:{subkey}" if subkey else key

            if entry is not None:
                if entry.schema_version >= schema_version:
                    entry.last_accessed = time.time()
                    self.hits[stat_key] = self.hits.get(stat_key, 0) + 1
                    return entry.value
                else:
                    logger.info(
                        "Stale cache entry invalidated for %s/%s:%s "
                        "(v%d < expected v%d)",
                        repo_name,
                        key,
                        subkey,
                        entry.schema_version,
                        schema_version,
                    )
                    self.invalidate(repo_name, key, subkey)

            self.misses[stat_key] = self.misses.get(stat_key, 0) + 1
            return None

    def set(
        self,
        repo_name: str,
        key: str,
        value: Any,
        schema_version: int,
        subkey: Optional[str] = None,
    ) -> None:
        """Store an object in the cache with its schema version."""
        with self._lock:
            cache_key = (repo_name, key, subkey)
            self._cache[cache_key] = CacheEntry(value, schema_version)
            logger.debug(
                "Cached entry for %s/%s:%s (v%d)",
                repo_name,
                key,
                subkey,
                schema_version,
            )

    def invalidate(
        self,
        repo_name: str,
        key: Optional[str] = None,
        subkey: Optional[str] = None,
    ) -> None:
        """Invalidate cache entries.

        If key is None, invalidates all keys for the repo.
        If subkey is None, invalidates all subkeys for the key.
        Otherwise invalidates only the specific subkey.
        """
        with self._lock:
            if key is None:
                to_remove = [k for k in self._cache.keys() if k[0] == repo_name]
            elif subkey is None:
                to_remove = [
                    k for k in self._cache.keys() if k[0] == repo_name and k[1] == key
                ]
            else:
                to_remove = [(repo_name, key, subkey)]

            for k in to_remove:
                self._cache.pop(k, None)

    def clear(self) -> None:
        """Clear all cache contents and statistics."""
        with self._lock:
            self._cache.clear()
            self.hits.clear()
            self.misses.clear()

    def get_stats(self) -> Dict[str, Any]:
        """Return hit/miss statistics and current size of the cache."""
        with self._lock:
            return {
                "hits": dict(self.hits),
                "misses": dict(self.misses),
                "size": len(self._cache),
            }
