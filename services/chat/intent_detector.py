"""Intent Detector — Phase 3.

Classifies user questions into structured intents so the IntentRouter can
delegate to the correct Repository Intelligence sub-system before falling back
to vector retrieval.

Design:
  - IntentDetector is an abstract interface (pluggable by design).
  - RuleBasedIntentDetector is the production implementation.
  - Zero LLM calls — pure regex/keyword matching for latency-free classification.
  - IntentResult carries the detected intent, confidence, and extracted entities
    to assist the router and context builder.
"""

from __future__ import annotations

import logging
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Intent enumeration
# ---------------------------------------------------------------------------


class Intent(str, Enum):
    """Supported intent types for repository chat questions."""

    ARCHITECTURE = "ARCHITECTURE"
    CIRCULAR_DEPENDENCY = "CIRCULAR_DEPENDENCY"
    API_SURFACE = "API_SURFACE"
    CALL_GRAPH = "CALL_GRAPH"
    SYMBOL = "SYMBOL"
    READING_ORDER = "READING_ORDER"
    IMPACT_ANALYSIS = "IMPACT_ANALYSIS"
    GENERAL_QA = "GENERAL_QA"
    UNKNOWN = "UNKNOWN"


@dataclass
class IntentResult:
    """Result of intent classification.

    Attributes:
        intent:     Detected intent category.
        confidence: 0.0–1.0 confidence in the classification.
        entities:   Extracted code entities (class names, function names, etc.)
                    mentioned in the question — used for pronoun injection.
        keywords:   The specific keywords that triggered this classification.
    """

    intent: Intent
    confidence: float = 1.0
    entities: List[str] = field(default_factory=list)
    keywords: List[str] = field(default_factory=list)

    def __repr__(self) -> str:
        return (
            f"IntentResult(intent={self.intent.value}, "
            f"confidence={self.confidence:.2f}, "
            f"entities={self.entities}, "
            f"keywords={self.keywords})"
        )


# ---------------------------------------------------------------------------
# Abstract interface
# ---------------------------------------------------------------------------


class IntentDetector(ABC):
    """Abstract interface for intent classifiers.

    Concrete implementations can be rule-based, ML-based, or LLM-based.
    The IntentRouter always calls detect() and never cares about implementation.
    """

    @abstractmethod
    def detect(self, question: str) -> IntentResult:
        """Classify the user question into an intent.

        Args:
            question: The (possibly pronoun-resolved) user question.

        Returns:
            IntentResult with the detected intent and supporting metadata.
        """


# ---------------------------------------------------------------------------
# Rule-based implementation
# ---------------------------------------------------------------------------

# Pattern groups: (compiled_regex, Intent, confidence_when_matched)
_RULE_TABLE: List[tuple] = [
    # Circular dependency — very specific signal words
    (
        re.compile(
            r"\b(circular|cycle|cyclic|circular.depend|import.loop|dependency.cycle)\b",
            re.I,
        ),
        Intent.CIRCULAR_DEPENDENCY,
        0.95,
    ),
    # Architecture — entry points, structure, layers, overview
    (
        re.compile(
            r"\b(architect|overview|entry.?point|module.structure"
            r"|design.of|high.?level|system.layout"
            r"|how.is.+organis|how.is.+organized"
            r"|system.design|monolith|microservice|code.structure"
            r"|project.structure)\b",
            re.I,
        ),
        Intent.ARCHITECTURE,
        0.90,
    ),
    # Reading order / onboarding
    (
        re.compile(
            r"\b(reading.?order|read.first|onboard|getting.started|where.to.start"
            r"|start.reading|best.order|understand.codebase|new.developer"
            r"|beginner|introduction.to)\b",
            re.I,
        ),
        Intent.READING_ORDER,
        0.90,
    ),
    # Call graph — callers, callees, who calls what
    (
        re.compile(
            r"\b(call.?graph|who.calls|what.calls|callers?.of|callees?.of"
            r"|call.chain|call.hierarchy|invocations?.of|called.by|calls.into)\b",
            re.I,
        ),
        Intent.CALL_GRAPH,
        0.90,
    ),
    # API surface — endpoints, public API, exported symbols
    (
        re.compile(
            r"\b(api.surface|public.api|endpoints?|routes?|exported|exports?"
            r"|public.methods?|rest.api|http.methods?|openapi|swagger"
            r"|fastapi.route|flask.route|express.route)\b",
            re.I,
        ),
        Intent.API_SURFACE,
        0.88,
    ),
    # Impact analysis — change impact, what breaks, risk
    (
        re.compile(
            r"\b(impact|blast.radius|what.breaks|what.changes|affected.files?"
            r"|ripple.effect|change.propagat|downstream|risk.of.changing"
            r"|side.effects?.of|what.depends.on|dependencies.of)\b",
            re.I,
        ),
        Intent.IMPACT_ANALYSIS,
        0.88,
    ),
    # Symbol lookup — find definition, where is, what is <CapWord>
    (
        re.compile(
            r"\b(where.is.+defined|where.is.+located|find.definition|where.is.defined"
            r"|find.the.class|what.is.the.definition|defined.in|declaration.of"
            r"|locate.the|definition.of|show.me.the.class|show.the.function)\b",
            re.I,
        ),
        Intent.SYMBOL,
        0.85,
    ),
    # General Q&A — fallback for common how/what/why questions
    (
        re.compile(
            r"\b(how.does|what.does|explain|describe|tell.me.about|summarize"
            r"|summarise|can.you.explain|help.me.understand|what.is.the.purpose"
            r"|why.does)\b",
            re.I,
        ),
        Intent.GENERAL_QA,
        0.70,
    ),
]

# Regex to extract PascalCase or camelCase identifiers as candidate entities
_ENTITY_PATTERN = re.compile(r"\b([A-Z][a-zA-Z0-9]{2,}(?:[A-Z][a-z0-9]+)*)\b")

# Regex for file path mentions
_FILE_PATTERN = re.compile(
    r"\b([\w./\\-]+\.(py|ts|tsx|js|jsx|java|go|rs|rb|php|cs|cpp|c|h|yml|yaml|json|md))\b",
    re.I,
)


class RuleBasedIntentDetector(IntentDetector):
    """Production intent detector using compiled regex rules.

    Matches the first (highest-priority) rule that fires. If no rule matches,
    returns UNKNOWN so the router falls through to vector search.
    """

    def detect(self, question: str) -> IntentResult:
        """Classify the question and extract entities.

        Rules are evaluated in declaration order. The first match wins.
        GENERAL_QA is a catch-all that appears near the bottom.
        """
        if not question or not question.strip():
            return IntentResult(intent=Intent.UNKNOWN, confidence=0.0)

        q = question.strip()
        matched_keywords: List[str] = []
        matched_intent: Optional[Intent] = None
        matched_confidence: float = 0.0

        for pattern, intent, confidence in _RULE_TABLE:
            m = pattern.search(q)
            if m:
                matched_intent = intent
                matched_confidence = confidence
                matched_keywords = [m.group(0)]
                break

        if matched_intent is None:
            matched_intent = Intent.UNKNOWN
            matched_confidence = 0.5

        # Extract code entities from the question regardless of intent
        entities = list(dict.fromkeys(_ENTITY_PATTERN.findall(q)))

        logger.debug(
            "IntentDetector: question=%r → intent=%s confidence=%.2f entities=%s",
            q[:80],
            matched_intent.value,
            matched_confidence,
            entities,
        )

        return IntentResult(
            intent=matched_intent,
            confidence=matched_confidence,
            entities=entities,
            keywords=matched_keywords,
        )
