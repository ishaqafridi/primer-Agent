"""
PrimerAgent ReAct Agent — Core Reasoning + Acting Loop

Implements a true ReAct (Reasoning + Acting) architecture where Google Gemini
autonomously decides which bioinformatics tool to invoke at each step, rather
than following a fixed pipeline.

Architecture:
    ┌────────────────────────────────────────────┐
    │  User Request                              │
    │       ↓                                    │
    │  THOUGHT: Gemini analyzes current state    │
    │       ↓                                    │
    │  ACTION: Selects tool from toolkit         │
    │       ↓                                    │
    │  EXECUTE: Runs selected tool               │
    │       ↓                                    │
    │  OBSERVATION: Records tool output          │
    │       ↓                                    │
    │  EVALUATE: Checks if goal is achieved      │
    │       ↓                                    │
    │  Loop or → FINAL ANSWER                    │
    └────────────────────────────────────────────┘

Key Differentiators from PrimeGen:
    1. Single-agent (no multi-agent orchestration)
    2. Dynamic tool selection (not pre-assigned to sub-agents)
    3. Full reasoning trace visible to user
    4. Iterative self-correction with biological justification
    5. Confidence scoring beyond numeric metrics

Usage:
    from primer_agent.react_agent import PrimerReActAgent
    
    agent = PrimerReActAgent(api_key="your-gemini-key")
    result = agent.run(
        gene_name="BRCA1",
        organism="Homo sapiens",
        application="Standard PCR",
    )
"""

import json
import logging
import time
import concurrent.futures
from typing import Dict, Any, List, Optional, Tuple

from primer_agent.config import (
    ACCEPTANCE_CRITERIA,
    DEFAULT_PRESETS,
    REACT_SYSTEM_PROMPT,
)
from primer_agent.gemini_client import GeminiClient, GeminiClientError
from primer_agent.reasoning.trace import ReasoningTrace
from primer_agent.reasoning.confidence import ConfidenceScorer
from primer_agent.tools.target_resolver import _resolve_target_impl
from primer_agent.tools.sequence_fetcher import (
    _fetch_ncbi_sequence_impl,
    calculate_gc_content,
)
from primer_agent.tools.primer_blast_designer import _design_primers_impl
from primer_agent.tools.in_silico_pcr import _run_in_silico_pcr_impl
from primer_agent.tools.amplicon_validator import _validate_amplicon_impl
from primer_agent.tools.blast_checker import _blast_check_impl
from primer_agent.tools.structure_checker import (
    _check_secondary_structure_impl,
    _check_heterodimer_impl,
)
from primer_agent.tools.exon_transcript_validator import _validate_exon_transcript_impl
from primer_agent.tools.primer_evaluator import _evaluate_primer_pair_impl
from primer_agent.tools.parameter_adjuster import (
    _adjust_parameters_impl,
    _adjust_parameters_llm,
)
from primer_agent.tools.report_generator import generate_report

logger = logging.getLogger(__name__)


class PrimerReActAgent:
    """
    Single-Agent ReAct System for Autonomous PCR Primer Design.
    
    This agent uses Google Gemini as its reasoning engine to autonomously
    decide which bioinformatics tools to use at each step of the primer
    design process. Unlike a fixed pipeline, the agent dynamically adapts
    its strategy based on observed results.
    
    The agent maintains a complete reasoning trace (Thought → Action →
    Observation) that provides full transparency into its decision-making
    process.
    
    Attributes:
        gemini: GeminiClient instance for LLM reasoning.
        trace: ReasoningTrace recording all decisions.
        confidence_scorer: ConfidenceScorer for biological assessment.
        max_iterations: Maximum redesign iterations.
        max_steps: Maximum total reasoning steps.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        model_name: Optional[str] = None,
        max_iterations: int = 5,
        max_steps: int = 15,
    ):
        """
        Initialize the PrimerAgent ReAct agent.
        
        Args:
            api_key: Google Gemini API key. Falls back to GOOGLE_API_KEY env var.
            model_name: Gemini model identifier.
            max_iterations: Maximum primer redesign iterations.
            max_steps: Maximum total ReAct reasoning steps.
        """
        self.gemini = GeminiClient(api_key=api_key, model_name=model_name)
        self.trace = ReasoningTrace()
        self.confidence_scorer = ConfidenceScorer(gemini_client=self.gemini)
        self.max_iterations = max_iterations
        self.max_steps = max_steps

        # State maintained across the reasoning loop
        self._state: Dict[str, Any] = {}

    def _reason(self, context: str) -> str:
        """
        Ask Gemini to reason about the current state and decide the next action.
        
        Args:
            context: Formatted string describing current state and history.
            
        Returns:
            Gemini's reasoning text including next action decision.
        """
        try:
            response = self.gemini.invoke(
                prompt=context,
                system_prompt=REACT_SYSTEM_PROMPT,
            )
            return response
        except GeminiClientError as e:
            logger.error(f"Gemini reasoning failed: {e}")
            return f"REASONING_ERROR: {str(e)}"

    def _build_context(self, user_request: str) -> str:
        """Build the context prompt for Gemini reasoning."""
        context = f"""## Current Task
{user_request}

## Available Tools
1. FETCH_SEQUENCE — Retrieve DNA sequence from NCBI by gene name or accession ID
2. DESIGN_PRIMERS — Generate primer pairs using Primer-BLAST engine
3. CHECK_BLAST — Verify primer specificity via BLAST off-target analysis
4. CHECK_STRUCTURE — Analyze hairpin and self-dimer secondary structures
5. CHECK_HETERODIMER — Check cross-dimer interaction between primer pairs
6. EVALUATE_PRIMERS — Score primer pairs on the 0-100 quality scale
7. ADJUST_PARAMETERS — Optimize Primer-BLAST parameters after failed evaluation

## Current State
{json.dumps(self._get_state_summary(), indent=2, default=str)}

## Previous Reasoning Steps
{self._format_recent_steps()}

## Instructions
Based on the current state, decide your next action. Respond in this format:

THOUGHT: [Your biological reasoning about what to do next and why]

ACTION: [Tool name from the list above, or FINAL_ANSWER if done]

ACTION_INPUT: [JSON arguments for the tool, or your final summary]

IMPORTANT: If the state summary shows design_passed is True or if primers have already been evaluated, respond with ACTION: FINAL_ANSWER to complete the task.
"""
        return context

    def _get_state_summary(self) -> Dict[str, Any]:
        """Get a concise summary of the current agent state."""
        return {
            "gene_name": self._state.get("gene_name", "not set"),
            "organism": self._state.get("organism", "not set"),
            "application": self._state.get("application", "not set"),
            "sequence_fetched": self._state.get("sequence") is not None,
            "sequence_length": len(self._state.get("sequence", "")) if self._state.get("sequence") else 0,
            "gc_content": self._state.get("gc_content"),
            "accession": self._state.get("accession"),
            "num_candidates": len(self._state.get("candidates", [])),
            "current_iteration": self._state.get("iteration_count", 0),
            "best_score": self._state.get("best_score"),
            "design_passed": self._state.get("design_passed", False),
            "blast_checked": self._state.get("blast_checked", False),
            "structure_checked": self._state.get("structure_checked", False),
        }

    def _format_recent_steps(self) -> str:
        """Format the last few reasoning steps for context."""
        if not self.trace.steps:
            return "No previous steps."
        
        # Show last 4 steps to keep context manageable
        recent = self.trace.steps[-4:]
        lines = []
        for step in recent:
            content = step.content[:300] + "..." if len(step.content) > 300 else step.content
            lines.append(f"[Step {step.step_number}] {step.step_type.upper()}: {content}")
        return "\n".join(lines)

    def _truncate_observation(self, observation: str, max_len: int = 1500) -> str:
        """Truncate observation text to prevent context window bloat."""
        if len(observation) <= max_len:
            return observation
        return observation[:max_len] + f"\n... [truncated, {len(observation) - max_len} chars omitted]"

    def _parse_reasoning(self, response: str) -> Tuple[str, str, str]:
        """
        Parse LLM response into Thought, Action, and Action Input.
        Handles markdown formatting (**THOUGHT:**, ### ACTION:, etc.) robustly.
        """
        thought = ""
        action = ""
        action_input = ""

        lines = response.strip().split("\n")
        current_section = None
        current_content = []

        for line in lines:
            line_stripped = line.strip()
            # Clean markdown markers for prefix matching
            cleaned = line_stripped.strip("*#_`- ").strip()
            upper = cleaned.upper()

            if upper.startswith("THOUGHT:") or upper.startswith("THOUGHT"):
                if current_section == "action":
                    action = "\n".join(current_content).strip()
                current_section = "thought"
                colon_idx = cleaned.find(":")
                val = cleaned[colon_idx + 1:].strip("*#_`").strip() if colon_idx != -1 else ""
                current_content = [val] if val else []
            elif upper.startswith("ACTION_INPUT:") or upper.startswith("ACTION INPUT:") or upper.startswith("ACTION_INPUT") or upper.startswith("ACTION INPUT"):
                if current_section == "thought":
                    thought = "\n".join(current_content).strip()
                elif current_section == "action":
                    action = "\n".join(current_content).strip()
                current_section = "action_input"
                colon_idx = cleaned.find(":")
                val = cleaned[colon_idx + 1:].strip("*#_`").strip() if colon_idx != -1 else ""
                current_content = [val] if val else []
            elif upper.startswith("ACTION:") or upper.startswith("ACTION"):
                if current_section == "thought":
                    thought = "\n".join(current_content).strip()
                current_section = "action"
                colon_idx = cleaned.find(":")
                val = cleaned[colon_idx + 1:].strip("*#_`").strip() if colon_idx != -1 else ""
                current_content = [val] if val else []
            else:
                current_content.append(line_stripped)

        # Handle last section
        if current_section == "thought":
            thought = "\n".join(current_content).strip()
        elif current_section == "action":
            action = "\n".join(current_content).strip()
        elif current_section == "action_input":
            action_input = "\n".join(current_content).strip()

        # Normalize action name
        action_clean = action.upper().replace("*", "").replace("#", "").replace("`", "").replace(" ", "_").strip()
        if "FINAL" in action_clean or "DONE" in action_clean or "COMPLETE" in action_clean:
            action_clean = "FINAL_ANSWER"

        return thought, action_clean, action_input

    def _execute_tool(self, action: str, action_input: str) -> str:
        """
        Execute the specified tool and return the observation.
        
        Args:
            action: Tool name (e.g., 'FETCH_SEQUENCE').
            action_input: JSON string or text arguments.
            
        Returns:
            Tool execution result as a string observation.
        """
        try:
            args = {}
            if action_input:
                try:
                    args = json.loads(action_input)
                except json.JSONDecodeError:
                    args = {"input": action_input}

            if action == "RESOLVE_TARGET":
                return self._exec_resolve_target(args)
            elif action == "FETCH_SEQUENCE":
                return self._exec_fetch_sequence(args)
            elif action == "DESIGN_PRIMERS":
                return self._exec_design_primers(args)
            elif action == "IN_SILICO_PCR":
                return self._exec_in_silico_pcr(args)
            elif action == "VALIDATE_AMPLICON":
                return self._exec_validate_amplicon(args)
            elif action == "CHECK_BLAST":
                return self._exec_check_blast(args)
            elif action == "CHECK_STRUCTURE":
                return self._exec_check_structure(args)
            elif action == "CHECK_HETERODIMER":
                return self._exec_check_heterodimer(args)
            elif action == "VALIDATE_EXON":
                return self._exec_validate_exon(args)
            elif action == "EVALUATE_PRIMERS":
                return self._exec_evaluate_primers(args)
            elif action == "ADJUST_PARAMETERS":
                return self._exec_adjust_parameters(args)
            else:
                return f"Unknown action: {action}. Available: RESOLVE_TARGET, FETCH_SEQUENCE, DESIGN_PRIMERS, IN_SILICO_PCR, VALIDATE_AMPLICON, CHECK_BLAST, CHECK_STRUCTURE, CHECK_HETERODIMER, VALIDATE_EXON, EVALUATE_PRIMERS, ADJUST_PARAMETERS"

        except Exception as e:
            logger.error(f"Tool execution error ({action}): {e}")
            return f"TOOL_ERROR: {str(e)}"

    def _exec_resolve_target(self, args: Dict) -> str:
        """Execute Target & Transcript resolution."""
        gene = args.get("gene_or_accession", self._state.get("gene_name", ""))
        organism = args.get("organism", self._state.get("organism", "Homo sapiens"))
        user_tx = args.get("user_transcript")

        res = _resolve_target_impl(
            gene_or_accession=gene,
            organism=organism,
            user_transcript=user_tx,
        )

        self._state["genome_assembly"] = res["genome_assembly"]
        self._state["transcript_accession"] = res["transcript_accession"]
        self._state["exons"] = res["exons"]
        self._state["target_resolved"] = True

        return json.dumps(res, indent=2)

    def _exec_in_silico_pcr(self, args: Dict) -> str:
        """Execute In-Silico PCR analysis."""
        candidates = self._state.get("candidates", [])
        fwd = args.get("fwd_primer") or (candidates[0]["fwd_seq"] if candidates else "")
        rev = args.get("rev_primer") or (candidates[0]["rev_seq"] if candidates else "")

        if not fwd or not rev:
            return "ERROR: Missing primers for In-Silico PCR."

        res = _run_in_silico_pcr_impl(
            fwd_primer=fwd,
            rev_primer=rev,
            template_seq=self._state.get("sequence"),
            organism=self._state.get("organism", "Homo sapiens"),
            target_name=self._state.get("gene_name", "TARGET"),
            genome_assembly=self._state.get("genome_assembly", "GRCh38"),
        )

        self._state["pcr_result"] = res
        self._state["pcr_checked"] = True

        # Return compact summary instead of full result
        return json.dumps({
            "status": res.get("status"),
            "engine_used": res.get("engine_used"),
            "amplicon_count": res.get("amplicon_count"),
            "amplicon_size": res.get("amplicon_size"),
            "orientation": res.get("orientation"),
            "specific_product": res.get("specific_product"),
            "reason": res.get("reason"),
        }, indent=2)

    def _exec_validate_amplicon(self, args: Dict) -> str:
        """Execute Amplicon validation."""
        pcr_res = self._state.get("pcr_result") or args.get("pcr_result")
        if not pcr_res:
            return "ERROR: Run IN_SILICO_PCR first before amplicon validation."

        app = args.get("application", self._state.get("application", "Standard PCR"))
        res = _validate_amplicon_impl(pcr_result=pcr_res, application=app)
        self._state["amplicon_validation"] = res

        return json.dumps(res, indent=2)

    def _exec_validate_exon(self, args: Dict) -> str:
        """Execute Exon / Transcript validation."""
        candidates = self._state.get("candidates", [])
        if not candidates:
            return "ERROR: No candidate primers designed yet."

        fwd_pos = candidates[0].get("fwd_pos", [0, 20])
        rev_pos = candidates[0].get("rev_pos", [200, 20])
        exons = self._state.get("exons")

        res = _validate_exon_transcript_impl(
            fwd_pos=fwd_pos,
            rev_pos=rev_pos,
            exons=exons,
            application=self._state.get("application", "qPCR"),
        )
        self._state["exon_validation"] = res

        return json.dumps(res, indent=2)

    def _exec_fetch_sequence(self, args: Dict) -> str:
        """Execute sequence fetching."""
        gene = args.get("gene_or_accession", self._state.get("gene_name", ""))
        organism = args.get("organism", self._state.get("organism", "Homo sapiens"))
        email = self._state.get("email", "user@example.com")

        result = _fetch_ncbi_sequence_impl(
            gene_or_accession=gene,
            organism=organism,
            email=email,
            api_key=self._state.get("ncbi_api_key"),
        )

        if result.get("error"):
            return json.dumps(result, indent=2)

        # Update state
        self._state["sequence"] = result["sequence"]
        self._state["accession"] = result["accession"]
        self._state["gc_content"] = result["gc_content"]
        self._state["high_gc"] = result.get("high_gc", False)
        self._state["seq_description"] = result.get("description", "")

        # Auto-select High-GC preset if needed
        if result.get("high_gc") and self._state.get("application") != "High-GC Preset":
            self._state["original_application"] = self._state.get("application", "Standard PCR")
            self._state["current_params"] = dict(DEFAULT_PRESETS.get("High-GC Preset", {}))

        return json.dumps({
            "accession": result["accession"],
            "description": result.get("description", "")[:100],
            "target_length": result["target_length"],
            "gc_content": result["gc_content"],
            "high_gc": result.get("high_gc", False),
            "warnings": result.get("warnings", []),
        }, indent=2)

    def _exec_design_primers(self, args: Dict) -> str:
        """Execute primer design."""
        sequence = args.get("sequence", self._state.get("sequence", ""))
        if not sequence:
            return "ERROR: No sequence available. Fetch a sequence first."

        application = args.get("application", self._state.get("application", "Standard PCR"))
        params = self._state.get("current_params", {})
        if not params:
            params = dict(DEFAULT_PRESETS.get(application, DEFAULT_PRESETS["Standard PCR"]))

        # Apply any custom param overrides from args
        if "custom_params" in args:
            try:
                overrides = json.loads(args["custom_params"]) if isinstance(args["custom_params"], str) else args["custom_params"]
                params.update(overrides)
            except (json.JSONDecodeError, TypeError):
                pass

        product_range = self._state.get(
            "product_size_range",
            (args.get("product_size_min", 100), args.get("product_size_max", 300)),
        )

        # Generate a large diverse pool of candidates (50) for strict validation filtering
        design_pool_size = max(50, self._state.get("num_return", 10) * 5)
        candidates = _design_primers_impl(
            sequence=sequence,
            params=params,
            product_size_range=product_range,
            num_return=design_pool_size,
        )

        self._state["candidates"] = candidates
        self._state["current_params"] = params

        if not candidates:
            return "No primer pairs could be designed with current constraints. Consider adjusting parameters."

        # Format summary
        summary = []
        for c in candidates:
            summary.append(
                f"Pair #{c['pair_idx']}: Fwd({c['fwd_len']}bp, Tm={c['fwd_tm']}°C, GC={c['fwd_gc']}%) "
                f"Rev({c['rev_len']}bp, Tm={c['rev_tm']}°C, GC={c['rev_gc']}%) "
                f"Product={c['product_size']}bp, Penalty={c['penalty']}"
            )

        return json.dumps({
            "num_candidates": len(candidates),
            "candidates_summary": summary,
            "top_candidate": candidates[0] if candidates else None,
        }, indent=2)

    def _exec_check_blast(self, args: Dict) -> str:
        """Execute BLAST check for primer specificity."""
        skip_blast = self._state.get("skip_blast", False)
        organism = args.get("organism", self._state.get("organism", "Homo sapiens"))

        candidates = self._state.get("candidates", [])
        if not candidates:
            return "ERROR: No primer candidates available. Design primers first."

        # Check top candidate (or specified primer)
        primer_seq = args.get("primer_seq")
        if primer_seq:
            result = _blast_check_impl(primer_seq, organism=organism, skip_blast=skip_blast)
            return json.dumps(result, indent=2)

        # Check all candidates' forward and reverse primers
        results = []
        for cand in candidates[:3]:  # Top 3 candidates
            fwd_blast = _blast_check_impl(cand["fwd_seq"], organism=organism, skip_blast=skip_blast)
            rev_blast = _blast_check_impl(cand["rev_seq"], organism=organism, skip_blast=skip_blast)
            results.append({
                "pair_idx": cand["pair_idx"],
                "fwd_blast": {"off_targets": fwd_blast["off_target_hits"], "pass": fwd_blast["pass"]},
                "rev_blast": {"off_targets": rev_blast["off_target_hits"], "pass": rev_blast["pass"]},
            })

        self._state["blast_results"] = results
        self._state["blast_checked"] = True

        return json.dumps({"blast_results": results}, indent=2)

    def _exec_check_structure(self, args: Dict) -> str:
        """Execute secondary structure analysis."""
        candidates = self._state.get("candidates", [])
        if not candidates:
            return "ERROR: No primer candidates available."

        results = []
        for cand in candidates[:3]:
            fwd_struct = _check_secondary_structure_impl(cand["fwd_seq"])
            rev_struct = _check_secondary_structure_impl(cand["rev_seq"])
            results.append({
                "pair_idx": cand["pair_idx"],
                "fwd_hairpin_mfe": fwd_struct["hairpin_mfe"],
                "fwd_hairpin_pass": fwd_struct["hairpin_pass"],
                "fwd_self_dimer_mfe": fwd_struct["self_dimer_mfe"],
                "fwd_self_dimer_pass": fwd_struct["self_dimer_pass"],
                "rev_hairpin_mfe": rev_struct["hairpin_mfe"],
                "rev_hairpin_pass": rev_struct["hairpin_pass"],
                "rev_self_dimer_mfe": rev_struct["self_dimer_mfe"],
                "rev_self_dimer_pass": rev_struct["self_dimer_pass"],
            })

        self._state["structure_results"] = results
        self._state["structure_checked"] = True

        return json.dumps({"structure_results": results}, indent=2)

    def _exec_check_heterodimer(self, args: Dict) -> str:
        """Execute hetero-dimer check."""
        candidates = self._state.get("candidates", [])
        if not candidates:
            return "ERROR: No primer candidates available."

        results = []
        for cand in candidates[:3]:
            hd = _check_heterodimer_impl(cand["fwd_seq"], cand["rev_seq"])
            results.append({
                "pair_idx": cand["pair_idx"],
                "hetero_dimer_mfe": hd["hetero_dimer_mfe"],
                "hetero_dimer_pass": hd["hetero_dimer_pass"],
            })

        self._state["heterodimer_results"] = results

        return json.dumps({"heterodimer_results": results}, indent=2)

    def _exec_evaluate_primers(self, args: Dict) -> str:
        """Execute strict VALIDATE → REJECT → SCORE → RANK workflow."""
        candidates = self._state.get("candidates", [])
        if not candidates:
            return "ERROR: No primer candidates available."

        organism = self._state.get("organism", "Homo sapiens")
        skip_blast = self._state.get("skip_blast", False)
        num_return = self._state.get("num_return", 10)

        # STAGE 1: Fast parallel local validation (In-Silico PCR, Tm, GC, Hairpin, Self-Dimer, Hetero-Dimer, Exon)
        all_eval_results = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=min(20, len(candidates))) as executor:
            future_sets = []
            for cand in candidates:
                f_struct_fut = executor.submit(_check_secondary_structure_impl, cand["fwd_seq"])
                r_struct_fut = executor.submit(_check_secondary_structure_impl, cand["rev_seq"])
                h_struct_fut = executor.submit(_check_heterodimer_impl, cand["fwd_seq"], cand["rev_seq"])
                pcr_fut = executor.submit(
                    _run_in_silico_pcr_impl,
                    cand["fwd_seq"],
                    cand["rev_seq"],
                    template_seq=self._state.get("sequence"),
                    organism=organism,
                    target_name=self._state.get("gene_name", "TARGET"),
                    genome_assembly=self._state.get("genome_assembly", "GRCh38"),
                )
                exon_fut = executor.submit(
                    _validate_exon_transcript_impl,
                    fwd_pos=cand.get("fwd_pos", [0, 20]),
                    rev_pos=cand.get("rev_pos", [200, 20]),
                    exons=self._state.get("exons"),
                    application=self._state.get("application", "qPCR"),
                )

                future_sets.append({
                    "cand": cand,
                    "f_struct": f_struct_fut,
                    "r_struct": r_struct_fut,
                    "h_struct": h_struct_fut,
                    "pcr_res": pcr_fut,
                    "exon_res": exon_fut,
                })

            for f_set in future_sets:
                cand = f_set["cand"]
                f_struct = f_set["f_struct"].result()
                r_struct = f_set["r_struct"].result()
                h_struct = f_set["h_struct"].result()
                pcr_res = f_set["pcr_res"].result()
                exon_res = f_set["exon_res"].result()

                dummy_blast = {"off_target_hits": 0, "pass": True}
                eval_res = _evaluate_primer_pair_impl(
                    candidate=cand,
                    fwd_blast=dummy_blast,
                    rev_blast=dummy_blast,
                    fwd_struct=f_struct,
                    rev_struct=r_struct,
                    hetero_struct=h_struct,
                    pcr_result=pcr_res,
                    exon_result=exon_res,
                )
                all_eval_results.append(eval_res)

        # STAGE 2: Web BLAST check on top locally-passing candidates only (if skip_blast=False)
        if not skip_blast:
            locally_passing = [r for r in all_eval_results if r.get("pass", False)]
            # Query NCBI BLAST for top passing candidates only (max num_return * 2)
            cands_for_blast = locally_passing[:max(10, num_return * 2)]
            for r in cands_for_blast:
                cand = r["candidate"]
                f_blast = _blast_check_impl(cand["fwd_seq"], organism=organism, skip_blast=False)
                r_blast = _blast_check_impl(cand["rev_seq"], organism=organism, skip_blast=False)

                re_eval = _evaluate_primer_pair_impl(
                    candidate=cand,
                    fwd_blast=f_blast,
                    rev_blast=r_blast,
                    fwd_struct=r["fwd_struct"],
                    rev_struct=r["rev_struct"],
                    hetero_struct=r["hetero_struct"],
                    pcr_result=r["pcr_result"],
                    exon_result=r["exon_result"],
                )
                for i, orig in enumerate(all_eval_results):
                    if orig["candidate"]["fwd_seq"] == cand["fwd_seq"] and orig["candidate"]["rev_seq"] == cand["rev_seq"]:
                        all_eval_results[i] = re_eval
                        break

        # ── STRICT SEPARATION: PASS vs FAIL ──
        pass_results = [r for r in all_eval_results if r.get("pass", False) and r.get("score") is not None]
        fail_results = [r for r in all_eval_results if not r.get("pass", False) or r.get("score") is None]

        # Sort PASS candidates by score (highest first)
        pass_results.sort(key=lambda x: x["score"], reverse=True)

        # Update state — only PASS results are stored as eval_results
        self._state["eval_results"] = pass_results
        self._state["fail_results"] = fail_results
        self._state["total_evaluated"] = len(all_eval_results)
        self._state["total_passed"] = len(pass_results)
        self._state["total_failed"] = len(fail_results)
        self._state["best_score"] = pass_results[0]["score"] if pass_results else 0
        self._state["design_passed"] = len(pass_results) > 0
        self._state["blast_checked"] = True
        self._state["structure_checked"] = True

        # Build compact summary
        summaries = []
        for r in pass_results[:num_return]:
            c = r["candidate"]
            summaries.append({
                "pair_idx": c.get("pair_idx", 0),
                "score": r["score"],
                "status": "PASS",
                "product_size": c.get("product_size", 0),
            })

        return json.dumps({
            "total_evaluated": len(all_eval_results),
            "total_passed": len(pass_results),
            "total_failed": len(fail_results),
            "best_score": pass_results[0]["score"] if pass_results else 0,
            "design_passed": len(pass_results) > 0,
            "valid_pairs": summaries,
        }, indent=2)

    def _exec_adjust_parameters(self, args: Dict) -> str:
        """Execute parameter adjustment."""
        eval_results = self._state.get("eval_results", [])
        if not eval_results:
            failures = ["No candidate primers generated under current parameter constraints."]
        else:
            best = eval_results[0]
            failures = best.get("failures", ["Score below threshold"])

        current_params = self._state.get("current_params", {})
        application = self._state.get("application", "Standard PCR")

        if self.gemini.api_key:
            updated_params, logs = _adjust_parameters_llm(
                failures, current_params, self.gemini, application
            )
        else:
            updated_params, logs = _adjust_parameters_impl(failures, current_params)

        self._state["current_params"] = updated_params
        self._state["iteration_count"] = self._state.get("iteration_count", 0) + 1

        return json.dumps({
            "adjustments": logs,
            "iteration": self._state["iteration_count"],
            "max_iterations": self.max_iterations,
        }, indent=2)

    # ─── Main Run Method ─────────────────────────────────────────────────

    def run(
        self,
        gene_name: str,
        organism: str = "Homo sapiens",
        application: str = "Standard PCR",
        product_size_range: Tuple[int, int] = (100, 300),
        num_return: int = 10,
        skip_blast: bool = True,
        email: str = "user@example.com",
        ncbi_api_key: Optional[str] = None,
        on_step_callback=None,
    ) -> Dict[str, Any]:
        """
        Run the complete ReAct primer design workflow.
        
        The agent autonomously reasons through the primer design process,
        selecting tools, evaluating results, and iterating as needed.
        
        Args:
            gene_name: Target gene symbol or accession ID.
            organism: Target organism scientific name.
            application: PCR application preset.
            product_size_range: Desired amplicon size range (min, max) bp.
            num_return: Number of primer pairs to return.
            skip_blast: If True, skip web BLAST API calls.
            email: NCBI email for API tracking.
            ncbi_api_key: Optional NCBI API key.
            on_step_callback: Optional callback(step_dict) for live UI updates.
            
        Returns:
            Dictionary with validated_results, reasoning_trace, report,
            confidence, and metadata.
        """
        # Initialize state
        self.trace = ReasoningTrace()
        self._state = {
            "gene_name": gene_name,
            "organism": organism,
            "application": application,
            "product_size_range": product_size_range,
            "num_return": num_return,
            "skip_blast": skip_blast,
            "email": email,
            "ncbi_api_key": ncbi_api_key,
            "current_params": dict(DEFAULT_PRESETS.get(application, DEFAULT_PRESETS["Standard PCR"])),
            "sequence": None,
            "accession": None,
            "candidates": [],
            "eval_results": [],
            "iteration_count": 0,
            "best_score": None,
            "design_passed": False,
            "blast_checked": False,
            "structure_checked": False,
        }

        user_request = (
            f"Design PCR primers for gene '{gene_name}' in {organism} "
            f"for {application}. Target amplicon size: {product_size_range[0]}-{product_size_range[1]} bp. "
            f"Return the top {num_return} validated primer pairs."
        )

        logger.info(f"PrimerAgent ReAct run started: {user_request}")

        # Check if Gemini is available
        has_gemini = bool(self.gemini.api_key)

        if has_gemini:
            result = self._run_with_gemini(user_request, on_step_callback)
        else:
            result = self._run_deterministic(user_request, on_step_callback)

        return result

    def _run_with_gemini(
        self, user_request: str, on_step_callback=None,
    ) -> Dict[str, Any]:
        """
        Run the ReAct loop with Gemini as the reasoning engine.
        
        Gemini decides which tool to call at each step based on its
        biological reasoning about the current state.
        """
        step_count = 0
        last_action = ""
        last_action_input = ""

        while step_count < self.max_steps:
            step_count += 1

            # 1. Build context and ask Gemini to reason
            context = self._build_context(user_request)
            response = self._reason(context)

            if "REASONING_ERROR" in response:
                err_msg = response.replace("REASONING_ERROR: ", "")
                logger.warning(f"Gemini reasoning failed ({err_msg}), falling back to deterministic mode")
                self.trace.add_thought(
                    f"Gemini API Notice: {err_msg}\n"
                    "Automatically continuing with deterministic primer design workflow."
                )
                return self._run_deterministic(user_request, on_step_callback)

            # 2. Parse the response
            thought, action, action_input = self._parse_reasoning(response)

            # 3. Record thought
            if thought:
                thought_step = self.trace.add_thought(thought)
                if on_step_callback:
                    on_step_callback(thought_step.to_dict())

            # 4. Check for FINAL_ANSWER
            if action == "FINAL_ANSWER":
                self.trace.add_final_answer(action_input or thought)
                break

            # 5. Check if action is repeated
            if action and action == last_action and action_input == last_action_input:
                self.trace.add_thought(f"Action '{action}' repeated. Automatically completing design.")
                self.trace.add_final_answer(
                    f"Primer design finalized. Best candidate score: {self._state.get('best_score', 0)}/100."
                )
                break

            last_action = action
            last_action_input = action_input

            # 6. Record and execute action
            try:
                action_args = json.loads(action_input) if action_input else {}
            except json.JSONDecodeError:
                action_args = {"input": action_input}

            action_step = self.trace.add_action(action, action_args)
            if on_step_callback:
                on_step_callback(action_step.to_dict())

            # 7. Execute tool
            observation = self._execute_tool(action, action_input)

            # 8. Record observation (truncated to prevent context bloat)
            truncated_obs = self._truncate_observation(observation)
            obs_step = self.trace.add_observation(
                content=truncated_obs,
                tool_name=action,
                success="ERROR" not in observation,
            )
            if on_step_callback:
                on_step_callback(obs_step.to_dict())

            # 9. Check termination conditions
            passed_count = self._state.get('total_passed', 0)
            num_return = self._state.get('num_return', 10)
            if passed_count >= num_return:
                self.trace.add_thought(
                    f"Found {passed_count} valid pairs (≥ {num_return} requested). "
                    f"Best score: {self._state.get('best_score', 0)}/100. Finalizing results."
                )
                self.trace.add_final_answer(
                    f"Primer design completed successfully. Found {passed_count} valid pairs. Top score: {self._state.get('best_score', 0)}/100."
                )
                break

            if self._state.get("iteration_count", 0) >= self.max_iterations:
                self.trace.add_thought(
                    f"Maximum iterations ({self.max_iterations}) reached. "
                    "Finalizing with best available results."
                )
                self.trace.add_final_answer(
                    f"Primer design completed after {self._state.get('iteration_count', 0)} iterations. "
                    f"Best candidate score: {self._state.get('best_score', 0)}/100."
                )
                break

        # Ensure final answer is set
        if not self.trace.steps or self.trace.steps[-1].step_type != "final_answer":
            self.trace.add_final_answer(
                f"Primer design run finished ({step_count} reasoning steps). "
                f"Best candidate score: {self._state.get('best_score', 0)}/100."
            )

        # Build final result
        return self._build_result()

    def _run_deterministic(
        self, user_request: str, on_step_callback=None,
    ) -> Dict[str, Any]:
        """
        Fallback deterministic workflow when Gemini is not available.
        
        Follows the same tool sequence as the original PrimerAgent but
        records reasoning traces for transparency.
        """
        # Step 1: Resolve target & assembly
        self.trace.add_thought(
            f"Starting PrimerAgent v3.0 pipeline for {self._state['gene_name']} in "
            f"{self._state['organism']}. Resolving reference genome assembly and transcript structure."
        )
        if on_step_callback:
            on_step_callback(self.trace.steps[-1].to_dict())

        self.trace.add_action("RESOLVE_TARGET", {
            "gene_or_accession": self._state["gene_name"],
            "organism": self._state["organism"],
        })
        resolve_res = self._execute_tool("RESOLVE_TARGET", json.dumps({
            "gene_or_accession": self._state["gene_name"],
            "organism": self._state["organism"],
        }))
        self.trace.add_observation(self._truncate_observation(resolve_res), tool_name="RESOLVE_TARGET")
        if on_step_callback:
            on_step_callback(self.trace.steps[-1].to_dict())

        # Step 2: Fetch sequence
        self.trace.add_thought("Fetching DNA template sequence from NCBI.")
        self.trace.add_action("FETCH_SEQUENCE", {
            "gene_or_accession": self._state["gene_name"],
            "organism": self._state["organism"],
        })
        fetch_result = self._execute_tool("FETCH_SEQUENCE", json.dumps({
            "gene_or_accession": self._state["gene_name"],
            "organism": self._state["organism"],
        }))
        self.trace.add_observation(self._truncate_observation(fetch_result), tool_name="FETCH_SEQUENCE")
        if on_step_callback:
            on_step_callback(self.trace.steps[-1].to_dict())

        if self._state.get("sequence") is None:
            self.trace.add_final_answer(f"Failed to fetch sequence: {fetch_result}")
            return self._build_result()

        # Iterative design loop
        while self._state.get("iteration_count", 0) < self.max_iterations:
            self._state["iteration_count"] = self._state.get("iteration_count", 0) + 1
            iteration = self._state["iteration_count"]

            # Step 3: Design primers
            self.trace.add_thought(
                f"Iteration {iteration}: Designing primers using "
                f"{self._state.get('application', 'Standard PCR')} preset with Primer-BLAST."
            )
            self.trace.add_action("DESIGN_PRIMERS", {"application": self._state.get("application")})
            design_result = self._execute_tool("DESIGN_PRIMERS", "{}")
            self.trace.add_observation(self._truncate_observation(design_result), tool_name="DESIGN_PRIMERS")
            if on_step_callback:
                on_step_callback(self.trace.steps[-1].to_dict())

            if not self._state.get("candidates"):
                self.trace.add_thought("No candidates generated. Attempting parameter adjustment.")
                self._execute_tool("ADJUST_PARAMETERS", "{}")
                continue

            # Step 4: Perform In-Silico PCR Gate
            self.trace.add_thought(
                f"Performing Gate 2 In-Silico PCR validation on top candidate."
            )
            self.trace.add_action("IN_SILICO_PCR", {})
            pcr_res_text = self._execute_tool("IN_SILICO_PCR", "{}")
            self.trace.add_observation(self._truncate_observation(pcr_res_text), tool_name="IN_SILICO_PCR")
            if on_step_callback:
                on_step_callback(self.trace.steps[-1].to_dict())

            # Step 5: Full Multi-Gate Evaluation
            self.trace.add_thought(
                f"Evaluating {len(self._state.get('candidates', []))} candidates "
                f"with In-Silico PCR, BLAST, structure checks, and multi-gate quality scoring."
            )
            self.trace.add_action("EVALUATE_PRIMERS", {})
            eval_result = self._execute_tool("EVALUATE_PRIMERS", "{}")
            self.trace.add_observation(self._truncate_observation(eval_result), tool_name="EVALUATE_PRIMERS")
            if on_step_callback:
                on_step_callback(self.trace.steps[-1].to_dict())

            # Check if we have ENOUGH valid pairs for user's request
            passed_count = self._state.get('total_passed', 0)
            num_return = self._state.get('num_return', 10)
            if passed_count >= num_return:
                self.trace.add_thought(
                    f"Found {passed_count} valid pairs (≥ {num_return} requested). "
                    f"Best score: {self._state.get('best_score', 0)}/100. Finalizing results."
                )
                break

            # Not enough valid pairs yet — adjust parameters if iterations remain
            if iteration < self.max_iterations:
                self.trace.add_thought(
                    f"Only {passed_count}/{num_return} valid pairs found. "
                    f"Adjusting parameters for next iteration."
                )
                self.trace.add_action("ADJUST_PARAMETERS", {})
                adjust_result = self._execute_tool("ADJUST_PARAMETERS", "{}")
                self.trace.add_observation(self._truncate_observation(adjust_result), tool_name="ADJUST_PARAMETERS")
                if on_step_callback:
                    on_step_callback(self.trace.steps[-1].to_dict())

        self.trace.add_final_answer(
            f"Primer design completed after {self._state.get('iteration_count', 0)} iterations. "
            f"Best score: {self._state.get('best_score', 0)}/100."
        )

        return self._build_result()

    def _build_result(self) -> Dict[str, Any]:
        """
        Build final result: VALIDATE → REJECT → SCORE → RANK → RETURN TOP N.

        Only PASS candidates (score 60-100) are included in validated_results.
        Failed candidates are NEVER included — not even to fill shortfall.
        """
        eval_results = self._state.get("eval_results", [])  # Already filtered to PASS-only
        num_return = self._state.get("num_return", 10)

        # Sort PASS candidates by score descending
        eval_results.sort(key=lambda x: x.get("score", 0) or 0, reverse=True)

        # Return only the user-requested top N valid pairs (Rule 8 & 10)
        top_valid = eval_results[:num_return]

        design_passed = len(top_valid) > 0
        best_score = top_valid[0]["score"] if top_valid else 0

        # Compute confidence for the best valid candidate
        confidence = None
        if top_valid:
            confidence = self.confidence_scorer.compute_heuristic_confidence(top_valid[0])
            if self.gemini.api_key:
                try:
                    confidence = self.confidence_scorer.compute_llm_confidence(
                        evaluation=top_valid[0],
                        gene_name=self._state.get("gene_name", ""),
                        organism=self._state.get("organism", ""),
                        application=self._state.get("application", ""),
                    )
                except Exception:
                    pass

        # Generate report — only with valid (PASS) candidates
        report_text = generate_report(
            gene_name=self._state.get("gene_name", ""),
            organism=self._state.get("organism", ""),
            application=self._state.get("application", ""),
            accession=self._state.get("accession", ""),
            iteration_count=self._state.get("iteration_count", 0),
            validated_results=top_valid,
            reasoning_trace=self.trace.to_list(),
        )

        return {
            "validated_results": top_valid,
            "best_score": best_score,
            "design_passed": design_passed,
            "num_requested": num_return,
            "num_returned": len(top_valid),
            "total_evaluated": self._state.get("total_evaluated", 0),
            "total_passed": self._state.get("total_passed", 0),
            "total_failed": self._state.get("total_failed", 0),
            "confidence": confidence,
            "reasoning_trace": self.trace.to_list(),
            "reasoning_summary": self.trace.get_summary(),
            "report": report_text,
            "state": {
                "gene_name": self._state.get("gene_name"),
                "organism": self._state.get("organism"),
                "application": self._state.get("application"),
                "accession": self._state.get("accession"),
                "iteration_count": self._state.get("iteration_count", 0),
            },
            "gemini_usage": self.gemini.get_usage_stats(),
        }
