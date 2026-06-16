"""Evaluation Agent module.

Responsible for evaluating agent responses, validating citations,
detecting hallucinations, and scoring answer confidence.
"""

from typing import List, Optional
from google import genai
from models import EvaluationResult


class EvaluationAgent:
    """Agent that performs quality checks, citation verification, and confidence scoring on outputs."""

    def __init__(self, client: Optional[genai.Client] = None) -> None:
        """Initializes the EvaluationAgent.

        Args:
            client: An optional instance of Google GenAI client.
        """
        # TODO: Initialize client and configurations
        self.client = client

    def evaluate_response(self, prompt: str, response: str, source_contexts: List[str]) -> EvaluationResult:
        """Evaluates whether the agent response matches references and contains valid citations.

        Args:
            prompt: The original question or prompt.
            response: The generated response to evaluate.
            source_contexts: Code/document contexts cited or used by the generating agent.

        Returns:
            An EvaluationResult model.
        """
        # TODO: Validate citations and detect hallucinations using LLM or heuristics
        raise NotImplementedError("evaluate_response is not yet implemented.")
