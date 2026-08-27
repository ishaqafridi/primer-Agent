"""
🧬 PrimerAgent — Autonomous PCR Primer Design & Validation Agent

This module provides the core bioinformatics tools, LangGraph state graph,
and workflow entry points for PrimerAgent. Core implementations are modularized
in the `primer_agent` package for clean code organization and maintainability.
"""

import os
import sys
import time
import logging
from typing import Dict, List, Any, Optional, Tuple, TypedDict

import streamlit as st

# Import configuration constants
from primer_agent.config import (
    ACCEPTANCE_CRITERIA,
    DEFAULT_PRESETS,
    SUPPORTED_ORGANISMS,
)

# Import bioinformatics tools
from primer_agent.tools.target_resolver import _resolve_target_impl as resolve_target
from primer_agent.tools.sequence_fetcher import (
    calculate_gc_content,
    mask_low_complexity,
    _fetch_ncbi_sequence_impl as fetch_ncbi_sequence,
)
from primer_agent.tools.primer_blast_designer import _design_primers_impl as design_primers_blast
from primer_agent.tools.in_silico_pcr import _run_in_silico_pcr_impl as run_in_silico_pcr
from primer_agent.tools.blast_checker import _blast_check_impl as blast_check_primer
from primer_agent.tools.structure_checker import (
    _check_secondary_structure_impl as check_secondary_structure,
    _check_heterodimer_impl as check_heterodimer,
)
from primer_agent.tools.exon_transcript_validator import _validate_exon_transcript_impl as validate_exon_transcript
from primer_agent.tools.primer_evaluator import _evaluate_primer_pair_impl as evaluate_primer_pair
from primer_agent.tools.parameter_adjuster import _adjust_parameters_impl as adjust_parameters
from primer_agent.tools.report_generator import generate_report

# Import ReAct Agent and DB
from primer_agent.react_agent import PrimerReActAgent
from primer_agent.database.sqlite_store import PrimerDatabase

logger = logging.getLogger(__name__)

# Check optional dependencies
try:
    from Bio import Entrez, SeqIO
    from Bio.Blast import NCBIWWW, NCBIXML
    BIOPYTHON_AVAILABLE = True
except ImportError:
    BIOPYTHON_AVAILABLE = False

try:
    from langgraph.graph import StateGraph, END
    LANGGRAPH_AVAILABLE = True
except ImportError:
    LANGGRAPH_AVAILABLE = False


# ==============================================================================
# LANGGRAPH STATEFUL WORKFLOW & NODES
# ==============================================================================

class AgentState(TypedDict):
    gene_name: str
    organism: str
    application: str
    product_size_range: Tuple[int, int]
    num_return: int
    validated_results: Optional[List[Dict[str, Any]]]
    email: str
    api_key: Optional[str]
    skip_blast: bool
    sequence: Optional[str]
    accession: Optional[str]
    candidates: Optional[List[Dict[str, Any]]]
    evaluation: Optional[Dict[str, Any]]
    current_params: Dict[str, Any]
    iteration_count: int
    best_result: Optional[Dict[str, Any]]
    final_report: Optional[str]
    step_log: List[Dict[str, Any]]
    error: Optional[str]


def parse_input_node(state: AgentState) -> Dict[str, Any]:
    """Node 1: Validate and initialize input state."""
    app_preset = DEFAULT_PRESETS.get(state["application"], DEFAULT_PRESETS["Standard PCR"])
    step_log = list(state.get("step_log", []))
    step_log.append({
        "step": "parse_input",
        "title": "📥 Step 1: Input Parsing & Preset Initialization",
        "details": f"Target: '{state['gene_name']}' in {state['organism']} | Application: {state['application']} | Product Range: {state['product_size_range'][0]}-{state['product_size_range'][1]} bp"
    })

    return {
        "current_params": dict(app_preset),
        "iteration_count": 0,
        "step_log": step_log,
        "error": None
    }


def fetch_sequence_node(state: AgentState) -> Dict[str, Any]:
    """Node 2: Fetch sequence from NCBI Entrez API."""
    step_log = list(state["step_log"])

    seq_data = fetch_ncbi_sequence(
        gene_or_accession=state["gene_name"],
        organism=state["organism"],
        email=state.get("email", "user@example.com"),
        api_key=state.get("api_key")
    )

    if seq_data.get("error"):
        step_log.append({
            "step": "fetch_sequence",
            "title": "❌ Step 2: NCBI Sequence Fetch Failed",
            "details": seq_data["error"]
        })
        return {"error": seq_data["error"], "step_log": step_log}

    # High GC detection auto preset adjustment
    params = dict(state["current_params"])
    if seq_data.get("high_gc"):
        params.update(DEFAULT_PRESETS["High-GC Preset"])

    step_log.append({
        "step": "fetch_sequence",
        "title": "🧬 Step 2: NCBI Sequence Fetched Successfully",
        "details": f"Accession: {seq_data['accession']} | Length: {seq_data['target_length']:,} bp | GC Content: {seq_data['gc_content']:.1f}%" +
                   (f" | Warnings: {'; '.join(seq_data['warnings'])}" if seq_data['warnings'] else "")
    })

    return {
        "sequence": seq_data["sequence"],
        "accession": seq_data["accession"],
        "current_params": params,
        "step_log": step_log
    }


def design_primers_node(state: AgentState) -> Dict[str, Any]:
    """Node 3: Run Primer-BLAST to generate top candidate pairs."""
    step_log = list(state["step_log"])

    candidates = design_primers_blast(
        sequence=state["sequence"],
        params=state["current_params"],
        product_size_range=state["product_size_range"]
    )

    if not candidates:
        step_log.append({
            "step": "design_primers",
            "title": "⚠️ Step 3: Primer-BLAST Design Produced 0 Candidates",
            "details": "No primer pairs met the initial constraints."
        })
        return {"candidates": [], "step_log": step_log}

    step_log.append({
        "step": "design_primers",
        "title": f"🧪 Step 3: Primer-BLAST Generated {len(candidates)} Candidates (Iteration {state['iteration_count'] + 1})",
        "details": f"Top Candidate #1: Fwd ({candidates[0]['fwd_len']}bp, Tm={candidates[0]['fwd_tm']}°C), Rev ({candidates[0]['rev_len']}bp, Tm={candidates[0]['rev_tm']}°C), Product={candidates[0]['product_size']}bp"
    })

    return {"candidates": candidates, "step_log": step_log}


def evaluate_candidate_list_in_parallel(candidates: List[Dict[str, Any]], organism: str, skip_blast: bool, num_return: int) -> List[Dict[str, Any]]:
    """Evaluate candidate primers in parallel using ThreadPoolExecutor."""
    import concurrent.futures
    cands_to_eval = candidates[:num_return]
    results = []

    with concurrent.futures.ThreadPoolExecutor(max_workers=min(15, max(1, len(cands_to_eval) * 5))) as executor:
        future_sets = []
        for cand in cands_to_eval:
            f_blast_fut = executor.submit(blast_check_primer, cand["fwd_seq"], organism=organism, skip_blast=skip_blast)
            r_blast_fut = executor.submit(blast_check_primer, cand["rev_seq"], organism=organism, skip_blast=skip_blast)
            f_struct_fut = executor.submit(check_secondary_structure, cand["fwd_seq"])
            r_struct_fut = executor.submit(check_secondary_structure, cand["rev_seq"])
            h_struct_fut = executor.submit(check_heterodimer, cand["fwd_seq"], cand["rev_seq"])

            future_sets.append({
                "cand": cand,
                "f_blast": f_blast_fut,
                "r_blast": r_blast_fut,
                "f_struct": f_struct_fut,
                "r_struct": r_struct_fut,
                "h_struct": h_struct_fut
            })

        for f_set in future_sets:
            cand = f_set["cand"]
            f_blast = f_set["f_blast"].result()
            r_blast = f_set["r_blast"].result()
            f_struct = f_set["f_struct"].result()
            r_struct = f_set["r_struct"].result()
            h_struct = f_set["h_struct"].result()

            eval_res = evaluate_primer_pair(
                candidate=cand,
                fwd_blast=f_blast,
                rev_blast=r_blast,
                fwd_struct=f_struct,
                rev_struct=r_struct,
                hetero_struct=h_struct
            )
            results.append(eval_res)

    return results


def blast_and_structure_node(state: AgentState) -> Dict[str, Any]:
    """Nodes 4 & 5: Perform BLAST check and secondary structure audit on candidates."""
    step_log = list(state["step_log"])
    candidates = state.get("candidates", [])
    num_return = state.get("num_return", 3)

    if not candidates:
        return {"step_log": step_log}

    eval_results = evaluate_candidate_list_in_parallel(
        candidates=candidates,
        organism=state["organism"],
        skip_blast=state.get("skip_blast", False),
        num_return=num_return
    )

    eval_results.sort(key=lambda x: x["score"], reverse=True)

    top_res = eval_results[0]
    score = top_res["score"]
    pass_flag = top_res["pass"]

    step_log.append({
        "step": "evaluate",
        "title": f"📊 Step 4-5: Candidate Evaluation Complete — Evaluated {len(eval_results)} Pairs",
        "details": f"Top Candidate Score: {score}/100 ({'PASS 🟢' if pass_flag else 'FAIL 🔴'}) | " +
                   f"Scores: {', '.join([str(r['score']) for r in eval_results])}"
    })

    existing_validated = state.get("validated_results") or []
    unique_results = {}
    for r in existing_validated + eval_results:
        key = (r["candidate"]["fwd_seq"], r["candidate"]["rev_seq"])
        if key not in unique_results or r["score"] > unique_results[key]["score"]:
            unique_results[key] = r

    sorted_unique = sorted(unique_results.values(), key=lambda x: x["score"], reverse=True)
    best_validated_list = sorted_unique[:num_return]
    best_res = best_validated_list[0] if best_validated_list else None

    return {
        "evaluation": top_res,
        "best_result": best_res,
        "validated_results": best_validated_list,
        "step_log": step_log
    }


def iterate_critic_node(state: AgentState) -> Dict[str, Any]:
    """Node 6: Parameter Adjuster (Critic) alters constraints for next iteration."""
    step_log = list(state["step_log"])
    eval_res = state.get("evaluation", {})
    failures = eval_res.get("failures", ["Low quality score"])
    current_params = state["current_params"]
    iter_count = state["iteration_count"] + 1

    updated_params, logs = adjust_parameters(failures, current_params)

    step_log.append({
        "step": "iterate",
        "title": f"🔄 Step 6: Parameter Adjuster Critic (Iteration {iter_count} -> {iter_count + 1})",
        "details": " | ".join(logs)
    })

    return {
        "current_params": updated_params,
        "iteration_count": iter_count,
        "step_log": step_log
    }


def report_node(state: AgentState) -> Dict[str, Any]:
    """Node 7: Produce final structured report."""
    step_log = list(state["step_log"])
    report_text = generate_report(state)

    best_res = state.get("best_result") or {}
    score = best_res.get("score", 0)

    step_log.append({
        "step": "report",
        "title": "📋 Step 7: Validation Report Formatted",
        "details": f"Final report generated successfully. Result: {score}/100"
    })

    return {
        "final_report": report_text,
        "step_log": step_log
    }


def should_continue(state: AgentState) -> str:
    """Conditional Edge: Route to 'report' if score >= 70 or max iterations reached, else 'iterate'."""
    if state.get("error"):
        return "report"

    eval_res = state.get("evaluation", {})
    pass_flag = eval_res.get("pass", False)
    iter_count = state.get("iteration_count", 0)

    if pass_flag or iter_count >= ACCEPTANCE_CRITERIA["max_iterations"] - 1:
        return "report"
    return "iterate"


def build_primer_agent_graph():
    """Construct and compile the LangGraph state graph."""
    builder = StateGraph(AgentState)

    builder.add_node("parse_input", parse_input_node)
    builder.add_node("fetch_sequence", fetch_sequence_node)
    builder.add_node("design_primers", design_primers_node)
    builder.add_node("blast_and_structure", blast_and_structure_node)
    builder.add_node("iterate", iterate_critic_node)
    builder.add_node("report", report_node)

    builder.set_entry_point("parse_input")

    builder.add_edge("parse_input", "fetch_sequence")
    builder.add_edge("fetch_sequence", "design_primers")
    builder.add_edge("design_primers", "blast_and_structure")

    builder.add_conditional_edges(
        "blast_and_structure",
        should_continue,
        {
            "iterate": "iterate",
            "report": "report"
        }
    )

    builder.add_edge("iterate", "design_primers")
    builder.add_edge("report", END)

    return builder.compile()


def run_manual_agent_workflow(initial_state: Dict[str, Any]) -> Dict[str, Any]:
    """Execute the agent workflow iteratively without LangGraph library dependency."""
    state = dict(initial_state)

    state.update(parse_input_node(state))

    fetch_out = fetch_sequence_node(state)
    state.update(fetch_out)
    if state.get("error"):
        state.update(report_node(state))
        return state

    while state["iteration_count"] < ACCEPTANCE_CRITERIA["max_iterations"]:
        design_out = design_primers_node(state)
        state.update(design_out)

        eval_out = blast_and_structure_node(state)
        state.update(eval_out)

        eval_res = state.get("evaluation", {})
        if eval_res.get("pass", False):
            break

        if state["iteration_count"] >= ACCEPTANCE_CRITERIA["max_iterations"] - 1:
            break

        iter_out = iterate_critic_node(state)
        state.update(iter_out)

    report_out = report_node(state)
    state.update(report_out)

    return state


# ==============================================================================
# STREAMLIT USER INTERFACE ENTRY POINT
# ==============================================================================

def main():
    """Streamlit entry point for running PrimerAgent directly."""
    from app import main as app_main
    app_main()


if __name__ == "__main__":
    main()
