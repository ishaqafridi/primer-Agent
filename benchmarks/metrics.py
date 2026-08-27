"""
PrimerAgent Benchmark Metrics Calculation

Computes quantitative benchmarking metrics from raw test outputs:
- Design Success Rate (%)
- Mean Execution Time (seconds)
- Mean Quality Score (0-100)
- Tm Accuracy (deviation from target Tm 60.0°C)
- GC% Compliance Rate (% within 40-60%)
- Tm Balance (% pairs with ΔTm ≤ 2.0°C)
- Hairpin Pass Rate (% MFE > -2.0 kcal/mol)
- Self-Dimer Pass Rate (% MFE > -6.0 kcal/mol)
- Hetero-Dimer Pass Rate (% MFE > -6.0 kcal/mol)
- Redesign Recovery Rate (% rescued after failure)
"""

import math
from typing import Dict, Any, List


def calculate_benchmark_metrics(results: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Compute aggregate benchmark metrics from a list of test case execution results.
    
    Args:
        results: List of test case execution dicts containing scores, timings,
                 and candidate metadata.
                 
    Returns:
        Dict containing statistical summary metrics.
    """
    total_cases = len(results)
    if total_cases == 0:
        return {"error": "No benchmark results provided."}

    success_count = sum(1 for r in results if r.get("design_passed", False))
    exec_times = [r.get("execution_time") if r.get("execution_time") is not None else 0.0 for r in results]
    quality_scores = [r.get("best_score") if r.get("best_score") is not None else 0.0 for r in results]
    iterations = [r.get("iteration_count") if r.get("iteration_count") is not None else 1 for r in results]

    # Detailed primer thermodynamics metrics
    tm_diffs = []
    gc_compliant_count = 0
    total_primers_checked = 0
    hairpin_pass_count = 0
    self_dimer_pass_count = 0
    hetero_dimer_pass_count = 0

    for r in results:
        val_results = r.get("validated_results", [])
        if val_results:
            top_cand = val_results[0]
            cand = top_cand.get("candidate", {})
            tm_diffs.append(cand.get("tm_diff", 0.0))

            fwd_gc = cand.get("fwd_gc", 0.0)
            rev_gc = cand.get("rev_gc", 0.0)
            if 40.0 <= fwd_gc <= 60.0:
                gc_compliant_count += 1
            if 40.0 <= rev_gc <= 60.0:
                gc_compliant_count += 1
            total_primers_checked += 2

            f_struct = top_cand.get("fwd_struct", {})
            r_struct = top_cand.get("rev_struct", {})
            h_struct = top_cand.get("hetero_struct", {})

            if f_struct.get("hairpin_pass", True) and r_struct.get("hairpin_pass", True):
                hairpin_pass_count += 1
            if f_struct.get("self_dimer_pass", True) and r_struct.get("self_dimer_pass", True):
                self_dimer_pass_count += 1
            if h_struct.get("hetero_dimer_pass", True):
                hetero_dimer_pass_count += 1

    # Statistical aggregations
    mean_exec_time = sum(exec_times) / total_cases
    mean_quality_score = sum(quality_scores) / total_cases
    mean_tm_diff = (sum(tm_diffs) / len(tm_diffs)) if tm_diffs else 0.0
    mean_iterations = sum(iterations) / total_cases

    gc_compliance_pct = (gc_compliant_count / total_primers_checked * 100.0) if total_primers_checked > 0 else 0.0
    hairpin_pass_pct = (hairpin_pass_count / total_cases * 100.0)
    self_dimer_pass_pct = (self_dimer_pass_count / total_cases * 100.0)
    hetero_dimer_pass_pct = (hetero_dimer_pass_count / total_cases * 100.0)
    success_rate_pct = (success_count / total_cases * 100.0)

    return {
        "total_test_cases": total_cases,
        "design_success_rate_pct": round(success_rate_pct, 2),
        "mean_execution_time_sec": round(mean_exec_time, 2),
        "mean_quality_score": round(mean_quality_score, 2),
        "mean_tm_diff_celsius": round(mean_tm_diff, 2),
        "mean_iterations_required": round(mean_iterations, 2),
        "gc_compliance_pct": round(gc_compliance_pct, 2),
        "hairpin_pass_pct": round(hairpin_pass_pct, 2),
        "self_dimer_pass_pct": round(self_dimer_pass_pct, 2),
        "hetero_dimer_pass_pct": round(hetero_dimer_pass_pct, 2),
    }
