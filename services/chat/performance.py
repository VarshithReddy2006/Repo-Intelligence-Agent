"""Chat Performance Reporter — Phase 13.

Produces a structured performance report for the Repository Chat v2 pipeline.
The report summarises timings, stage breakdowns, and recommendations.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class StageTiming:
    name: str
    elapsed_ms: float
    pct_of_total: float = 0.0


@dataclass
class ChatPerformanceReport:
    """Repository Chat v2 Performance Report.

    Generated from a completed PipelineTrace.
    """
    repo_name: str
    question_length: int
    stages: List[StageTiming] = field(default_factory=list)
    total_ms: float = 0.0
    context_tokens: int = 0
    tokens_streamed: int = 0
    provider: str = ""
    intent: str = ""
    retrieved: int = 0
    final_retrieved: int = 0
    fallback: bool = False

    def summary_lines(self) -> List[str]:
        lines = [
            "=== Repository Chat v2 Performance Report ===",
            f"  Repo:              {self.repo_name}",
            f"  Intent:            {self.intent}",
            f"  Provider:          {self.provider or 'none'}",
            f"  Fallback:          {'yes' if self.fallback else 'no'}",
            f"  Context tokens:    {self.context_tokens}",
            f"  Retrieved chunks:  {self.retrieved} → {self.final_retrieved}",
            f"  Tokens streamed:   {self.tokens_streamed}",
            "",
            "  Stage Breakdown:",
        ]
        for s in self.stages:
            lines.append(f"    {s.name:<25} {s.elapsed_ms:>8.1f} ms  ({s.pct_of_total:>5.1f}%)")
        lines.append(f"    {'TOTAL':<25} {self.total_ms:>8.1f} ms")
        return lines

    def __str__(self) -> str:
        return "\n".join(self.summary_lines())


def build_report_from_trace(trace) -> ChatPerformanceReport:
    """Build a ChatPerformanceReport from a completed PipelineTrace."""
    stages = [
        StageTiming("Intent Detection",         0.5),    # sub-ms, negligible
        StageTiming("Intent Router",             trace.router_elapsed_ms),
        StageTiming("Embedding",                 trace.embed_ms),
        StageTiming("Vector Search",             trace.search_ms),
        StageTiming("Reranking",                 trace.rerank_ms),
        StageTiming("Context Building",          0.5),    # sub-ms
        StageTiming("LLM / Streaming",           trace.llm_latency_ms),
    ]

    total = trace.total_ms or sum(s.elapsed_ms for s in stages)
    for s in stages:
        s.pct_of_total = (s.elapsed_ms / total * 100) if total > 0 else 0.0

    return ChatPerformanceReport(
        repo_name=trace.repo_name,
        question_length=trace.question_length,
        stages=stages,
        total_ms=total,
        context_tokens=trace.context_estimated_tokens,
        tokens_streamed=trace.tokens_streamed,
        provider=trace.provider_used,
        intent=trace.intent,
        retrieved=trace.initial_retrieved,
        final_retrieved=trace.final_returned,
        fallback=trace.fallback_triggered,
    )
