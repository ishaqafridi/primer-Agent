"""
PrimerAgent Reasoning Module — Explainable AI Reasoning Traces

Provides data structures and utilities for recording and displaying
the ReAct agent's Thought → Action → Observation reasoning cycle.
"""

from primer_agent.reasoning.trace import (
    ThoughtStep,
    ActionStep,
    ObservationStep,
    ReasoningTrace,
)
from primer_agent.reasoning.confidence import ConfidenceScorer
