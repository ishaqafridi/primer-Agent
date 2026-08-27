"""
PrimerAgent Reasoning Trace — Explainable AI Decision Recording

Provides structured data classes for recording and displaying every step
of the ReAct agent's Thought → Action → Observation reasoning cycle.

Each reasoning step is timestamped and numbered, creating a full audit trail
that demonstrates the agent's decision-making process. This is a key
differentiator from PrimeGen and other tools: every decision is transparent.

Usage:
    trace = ReasoningTrace()
    trace.add_thought("The target gene BRCA1 is known to have high-GC exons...")
    trace.add_action("design_primers", {"sequence": "ATCG...", "application": "qPCR"})
    trace.add_observation("Generated 5 primer pair candidates. Top candidate score: 85/100")
"""

import json
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional


@dataclass
class ReasoningStep:
    """Base class for all reasoning steps in the ReAct trace."""
    step_number: int
    step_type: str  # "thought", "action", "observation", "final_answer"
    content: str
    timestamp: str = field(default_factory=lambda: datetime.now().strftime("%H:%M:%S"))
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize step to dictionary for JSON storage."""
        return {
            "step_number": self.step_number,
            "type": self.step_type,
            "content": self.content,
            "timestamp": self.timestamp,
            "metadata": self.metadata,
        }


@dataclass
class ThoughtStep(ReasoningStep):
    """
    Records the agent's internal reasoning / analysis.
    
    Example: "The target gene TP53 in Homo sapiens is a tumor suppressor.
    I should first fetch its RefSeq mRNA sequence, then design standard PCR
    primers with the default preset since no special conditions were mentioned."
    """
    def __init__(self, step_number: int, content: str, **kwargs):
        super().__init__(
            step_number=step_number,
            step_type="thought",
            content=content,
            **kwargs,
        )


@dataclass
class ActionStep(ReasoningStep):
    """
    Records the tool selected and its arguments.
    
    Example: Tool='fetch_sequence', Args={'gene_or_accession': 'TP53', 'organism': 'Homo sapiens'}
    """
    tool_name: str = ""
    tool_args: Dict[str, Any] = field(default_factory=dict)

    def __init__(self, step_number: int, tool_name: str, tool_args: Dict[str, Any], **kwargs):
        content = f"Tool: {tool_name} | Args: {json.dumps(tool_args, default=str)}"
        super().__init__(
            step_number=step_number,
            step_type="action",
            content=content,
            **kwargs,
        )
        self.tool_name = tool_name
        self.tool_args = tool_args

    def to_dict(self) -> Dict[str, Any]:
        d = super().to_dict()
        d["tool_name"] = self.tool_name
        d["tool_args"] = self.tool_args
        return d


@dataclass
class ObservationStep(ReasoningStep):
    """
    Records the output/result from a tool execution.
    
    Example: "Fetched sequence NM_000546.6 (2629 bp, 52.3% GC). No warnings."
    """
    tool_name: str = ""
    success: bool = True

    def __init__(self, step_number: int, content: str, tool_name: str = "",
                 success: bool = True, **kwargs):
        super().__init__(
            step_number=step_number,
            step_type="observation",
            content=content,
            **kwargs,
        )
        self.tool_name = tool_name
        self.success = success

    def to_dict(self) -> Dict[str, Any]:
        d = super().to_dict()
        d["tool_name"] = self.tool_name
        d["success"] = self.success
        return d


class ReasoningTrace:
    """
    Complete ordered record of all ReAct reasoning steps.
    
    Maintains the full Thought → Action → Observation trace for an
    entire primer design session. Supports serialization for database
    storage and display in the Streamlit UI.
    
    Attributes:
        steps: Ordered list of all reasoning steps.
        start_time: When the reasoning session began.
        session_id: Unique identifier for the session.
    """

    def __init__(self):
        self.steps: List[ReasoningStep] = []
        self.start_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self._step_counter = 0

    def _next_step(self) -> int:
        """Get the next step number."""
        self._step_counter += 1
        return self._step_counter

    def add_thought(self, content: str, **kwargs) -> ThoughtStep:
        """Record a thought/reasoning step."""
        step = ThoughtStep(
            step_number=self._next_step(),
            content=content,
            **kwargs,
        )
        self.steps.append(step)
        return step

    def add_action(self, tool_name: str, tool_args: Dict[str, Any], **kwargs) -> ActionStep:
        """Record a tool selection/invocation step."""
        step = ActionStep(
            step_number=self._next_step(),
            tool_name=tool_name,
            tool_args=tool_args,
            **kwargs,
        )
        self.steps.append(step)
        return step

    def add_observation(
        self, content: str, tool_name: str = "", success: bool = True, **kwargs,
    ) -> ObservationStep:
        """Record a tool execution result."""
        step = ObservationStep(
            step_number=self._next_step(),
            content=content,
            tool_name=tool_name,
            success=success,
            **kwargs,
        )
        self.steps.append(step)
        return step

    def add_final_answer(self, content: str) -> ReasoningStep:
        """Record the final answer / conclusion."""
        step = ReasoningStep(
            step_number=self._next_step(),
            step_type="final_answer",
            content=content,
        )
        self.steps.append(step)
        return step

    def to_list(self) -> List[Dict[str, Any]]:
        """Serialize entire trace to list of dictionaries."""
        return [step.to_dict() for step in self.steps]

    def to_json(self) -> str:
        """Serialize entire trace to JSON string."""
        return json.dumps({
            "start_time": self.start_time,
            "total_steps": len(self.steps),
            "steps": self.to_list(),
        }, indent=2, default=str)

    def get_summary(self) -> Dict[str, Any]:
        """Get a high-level summary of the reasoning trace."""
        thoughts = [s for s in self.steps if s.step_type == "thought"]
        actions = [s for s in self.steps if s.step_type == "action"]
        observations = [s for s in self.steps if s.step_type == "observation"]
        tools_used = list(set(
            s.tool_name for s in self.steps
            if hasattr(s, "tool_name") and s.tool_name
        ))

        return {
            "total_steps": len(self.steps),
            "thoughts": len(thoughts),
            "actions": len(actions),
            "observations": len(observations),
            "tools_used": tools_used,
            "start_time": self.start_time,
        }

    def format_for_display(self) -> str:
        """Format the trace for human-readable display."""
        lines = [f"🧠 ReAct Reasoning Trace ({len(self.steps)} steps)\n"]
        for step in self.steps:
            icon = {
                "thought": "💭",
                "action": "⚡",
                "observation": "👁️",
                "final_answer": "✅",
            }.get(step.step_type, "•")

            lines.append(
                f"[Step {step.step_number}] {icon} {step.step_type.upper()} "
                f"({step.timestamp})"
            )
            # Truncate very long content for display
            content = step.content
            if len(content) > 500:
                content = content[:500] + "..."
            lines.append(f"  {content}\n")

        return "\n".join(lines)
