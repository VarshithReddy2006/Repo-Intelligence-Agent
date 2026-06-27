"""Conversation Memory Store — Phase 2.

Lightweight in-process session memory that enables:
  - Pronoun/reference resolution ("it", "that class", "this file")
  - Follow-up question context (remembers last entity/file discussed)
  - Context carry-over across multiple turns

Design decisions:
  - NO long-term vector memory — this is intentionally lightweight.
  - Sessions keyed by (repo_name, session_id).
  - TTL-based expiry: sessions idle >30 min are evicted.
  - Thread-safe for concurrent FastAPI requests.
  - The session_id is optional; when absent a default per-repo session is used
    so the frontend requires zero changes.
"""

from __future__ import annotations

import threading
import time
import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

# Session TTL: 30 minutes of inactivity
_SESSION_TTL_SECONDS = 1800

# Maximum turns to keep in memory (older turns are pruned)
_MAX_TURNS = 20

# Maximum entities / files to track
_MAX_ENTITIES = 10
_MAX_FILES = 10


@dataclass
class ConversationTurn:
    """A single question-answer pair in a conversation."""

    role: str  # "user" or "assistant"
    content: str
    timestamp: float = field(default_factory=time.time)


@dataclass
class ConversationSession:
    """Per-session state tracked across turns.

    Attributes:
        session_id:       Unique identifier for this session.
        repo_name:        Repository this session is about.
        turns:            Chronological list of conversation turns.
        last_entities:    Recently mentioned code entities (classes, functions,
                          methods, interfaces).  Used for pronoun resolution.
        last_files:       Recently mentioned file paths.
        last_intent:      The IntentType of the last classified turn.
        last_active:      Unix timestamp of the last activity.
    """

    session_id: str
    repo_name: str
    turns: List[ConversationTurn] = field(default_factory=list)
    last_entities: List[str] = field(default_factory=list)
    last_files: List[str] = field(default_factory=list)
    last_intent: Optional[str] = None
    last_active: float = field(default_factory=time.time)

    def add_turn(self, role: str, content: str) -> None:
        """Append a turn and update last_active, pruning oldest if needed."""
        self.turns.append(ConversationTurn(role=role, content=content))
        self.last_active = time.time()
        # Prune oldest turns to keep memory bounded
        if len(self.turns) > _MAX_TURNS:
            self.turns = self.turns[-_MAX_TURNS:]

    def update_context(
        self,
        entities: List[str],
        files: List[str],
        intent: Optional[str] = None,
    ) -> None:
        """Update tracked entities, files, and last intent after a turn."""
        # Merge and deduplicate, keeping most recently mentioned first
        for e in reversed(entities):
            if e and e not in self.last_entities:
                self.last_entities.insert(0, e)
        self.last_entities = self.last_entities[:_MAX_ENTITIES]

        for f in reversed(files):
            if f and f not in self.last_files:
                self.last_files.insert(0, f)
        self.last_files = self.last_files[:_MAX_FILES]

        if intent:
            self.last_intent = intent
        self.last_active = time.time()

    def resolve_pronouns(self, question: str) -> str:
        """Expand known pronouns/references in the question using tracked context.

        Simple heuristic:
          "it" / "this" / "that" at start or after verb → inject last entity
          "these files" / "those files" → inject last files list
          "What calls it?" → "What calls {last_entity}?"
        """
        if not question:
            return question

        q_lower = question.lower().strip()

        # Replace isolated "it", "this", "that", "them" with last entity
        if self.last_entities:
            last = self.last_entities[0]
            pronouns = [
                " it ",
                " it?",
                " it.",
                " it,",
                " this?",
                " that?",
                " them ",
                " them?",
            ]
            for p in pronouns:
                if p in f" {q_lower} ":
                    question = question.replace(p.strip(), last, 1)
                    logger.debug(
                        "ConversationMemory: resolved pronoun '%s' → '%s'",
                        p.strip(),
                        last,
                    )
                    break

            # "What calls it?" pattern at sentence start
            if q_lower.startswith(("what calls it", "who calls it", "what uses it")):
                question = question.replace("it", last, 1)

        return question

    def get_history_for_llm(self) -> List[Dict]:
        """Return turns formatted for LLM provider history."""
        return [{"role": t.role, "content": t.content} for t in self.turns]

    @property
    def is_expired(self) -> bool:
        return (time.time() - self.last_active) > _SESSION_TTL_SECONDS


class ConversationMemoryStore:
    """Thread-safe store for all active conversation sessions.

    Usage::

        store = ConversationMemoryStore()
        session = store.get_or_create("owner/repo", "session-abc")
        question = session.resolve_pronouns(raw_question)
        session.add_turn("user", question)
        ...
        session.add_turn("assistant", answer)
        session.update_context(entities=["UserService"], files=["services/user.py"])
    """

    def __init__(self) -> None:
        self._sessions: Dict[str, ConversationSession] = {}
        self._lock = threading.Lock()

    def _session_key(self, repo_name: str, session_id: str) -> str:
        return f"{repo_name}::{session_id}"

    def get_or_create(
        self,
        repo_name: str,
        session_id: str = "default",
    ) -> ConversationSession:
        """Retrieve an existing session or create a new one.

        Also evicts expired sessions on every access (lazy GC).
        """
        key = self._session_key(repo_name, session_id)
        with self._lock:
            self._evict_expired()
            if key not in self._sessions:
                self._sessions[key] = ConversationSession(
                    session_id=session_id,
                    repo_name=repo_name,
                )
                logger.debug("ConversationMemory: new session key=%s", key)
            return self._sessions[key]

    def clear_session(self, repo_name: str, session_id: str = "default") -> None:
        """Explicitly remove a session (e.g., user pressed 'New Chat')."""
        key = self._session_key(repo_name, session_id)
        with self._lock:
            self._sessions.pop(key, None)

    def session_count(self) -> int:
        with self._lock:
            return len(self._sessions)

    def _evict_expired(self) -> None:
        """Remove sessions that have exceeded TTL. Must be called under lock."""
        expired = [k for k, s in self._sessions.items() if s.is_expired]
        for k in expired:
            del self._sessions[k]
        if expired:
            logger.debug(
                "ConversationMemory: evicted %d expired session(s)", len(expired)
            )


# ---------------------------------------------------------------------------
# Module-level singleton — shared across all requests in the process
# ---------------------------------------------------------------------------
conversation_memory = ConversationMemoryStore()
