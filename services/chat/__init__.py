"""Repository Chat v2 — Intelligence pipeline package.

Components:
  - ConversationMemoryStore   : lightweight in-process session memory
  - IntentDetector            : rule-based intent classification
  - IntentRouter              : routes intents to repository intelligence layer
  - ContextBuilder            : dynamic token budget + chunk dedup + compression
  - ProviderManager           : multi-provider orchestration with circuit breaker
  - RetrievalPipeline         : unified retrieve() / retrieve_stream() surface
  - ChatObservability         : structured logging for every pipeline stage
"""

from .conversation_memory import ConversationMemoryStore, ConversationSession
from .intent_detector import IntentDetector, Intent, RuleBasedIntentDetector
from .intent_router import IntentRouter, RepositoryIntelligence
from .context_builder import ContextBuilder
from .provider_manager import ProviderManager
from .retrieval_pipeline import RetrievalPipeline
from .observability import ChatObservability

__all__ = [
    "ConversationMemoryStore",
    "ConversationSession",
    "IntentDetector",
    "Intent",
    "RuleBasedIntentDetector",
    "IntentRouter",
    "RepositoryIntelligence",
    "ContextBuilder",
    "ProviderManager",
    "RetrievalPipeline",
    "ChatObservability",
]
