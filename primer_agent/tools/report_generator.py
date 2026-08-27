"""
Tool 7: Report Generator — Structured Primer Validation Reports

Generates comprehensive, publication-quality primer validation reports
including primer sequences, thermodynamic audits, BLAST specificity results,
QC badges, wet-lab recommendations, and the full ReAct reasoning trace.
"""

import logging
from datetime import datetime
from typing import Dict, Any, List, Optional

from primer_agent.config import ACCEPTANCE_CRITERIA

logger = logging.getLogger(__name__)


def generate_report(
    gene_name: Any = None,
    organism: str = "N/A",
    application: str = "N/A",
    accession: str = "N/A",
    iteration_count: int = 1,
    validated_results: Optional[List[Dict[str, Any]]] = None,
    reasoning_trace: Optional[List[Dict[str, Any]]] = None,
    error: Optional[str] = None,
) -> str:
    """
    Format a structured, human-readable primer validation report.
    Accepts either individual parameters or a state dictionary.
    """
    # Handle state dictionary passed as first positional parameter
    if isinstance(gene_name, dict):
        state = gene_name
        gene_name = state.get("gene_name", "N/A")
        organism = state.get("organism", "N/A")
        application = state.get("application", "N/A")
        accession = state.get("accession", "N/A")
        iteration_count = state.get("iteration_count", 1)
        validated_results = state.get("validated_results") or []
        if not validated_results:
            best_res = state.get("best_result")
            if best_res:
                validated_results = [best_res]
        reasoning_trace = state.get("reasoning_trace")
        error = state.get("error")

    gene_name = gene_name or "N/A"
    validated_results = validated_results or []
    if not validated_results:
        return f"""================================================================================
🧬 PRIMERAGENT AUTONOMOUS PCR PRIMER VALIDATION REPORT (FAILED)
================================================================================
Timestamp           : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
Target Gene Symbol  : {gene_name}
Organism            : {organism}
NCBI Accession      : {accession}
Application         : {application}
Optimization Rounds : {iteration_count}
Final Quality Score : 0.0 / 100
Overall Quality     : 🔴 FAIL (NO CANDIDATES DESIGNED)

--------------------------------------------------------------------------------
Agent Error / Message:
{error or 'No successful primer candidate met the acceptance criteria.'}
================================================================================
"""

    report = f"""================================================================================
🧬 PRIMERAGENT AUTONOMOUS PCR PRIMER VALIDATION REPORT
================================================================================
Timestamp           : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
Target Gene Symbol  : {gene_name}
Organism            : {organism}
NCBI Accession      : {accession}
Application         : {application}
Optimization Rounds : {iteration_count} / {ACCEPTANCE_CRITERIA['max_iterations']}
Total Pairs Designed: {len(validated_results)}
"""

    for idx, best_res in enumerate(validated_results, 1):
        candidate = best_res.get("candidate", {})
        score = best_res.get("score")
        pass_flag = best_res.get("pass", False)

        if pass_flag and score is not None:
            score_display = f"{score} / 100"
            status_badge = "🟢 PASS (VALIDATED)"
        else:
            score_display = "NOT SCORED"
            status_badge = "🔴 FAIL (EXCLUDED FROM RESULTS)"

        fwd_seq = candidate.get("fwd_seq", "N/A")
        rev_seq = candidate.get("rev_seq", "N/A")
        fwd_tm = candidate.get("fwd_tm", 0.0)
        rev_tm = candidate.get("rev_tm", 0.0)
        tm_diff = candidate.get("tm_diff", 0.0)
        fwd_gc = candidate.get("fwd_gc", 0.0)
        rev_gc = candidate.get("rev_gc", 0.0)
        prod_size = candidate.get("product_size", 0)

        fwd_struct = best_res.get("fwd_struct", {})
        rev_struct = best_res.get("rev_struct", {})
        hetero_struct = best_res.get("hetero_struct", {})
        fwd_blast = best_res.get("fwd_blast", {})
        rev_blast = best_res.get("rev_blast", {})
        failures = best_res.get("failures", [])

        # GC clamp values
        fwd_clamp = best_res.get("fwd_gc_clamp", {})
        rev_clamp = best_res.get("rev_gc_clamp", {})
        fwd_clamp_gc = fwd_clamp.get("gc_count", "N/A")
        rev_clamp_gc = rev_clamp.get("gc_count", "N/A")
        fwd_clamp_pass = fwd_clamp.get("pass", True)
        rev_clamp_pass = rev_clamp.get("pass", True)

        # Recommended wet-lab annealing temperature
        min_tm = min(fwd_tm, rev_tm) if fwd_tm and rev_tm else 60.0
        rec_ta = round(min_tm - 3.0, 1)

        report += f"""
================================================================================
PRIMER PAIR CANDIDATE #{idx} (Quality Score: {score_display} — {status_badge})
================================================================================
FORWARD PRIMER  (5' -> 3') : {fwd_seq}
  - Length                 : {len(fwd_seq)} bp
  - Melting Temp (Tm)      : {fwd_tm} °C
  - GC Content             : {fwd_gc} %
  - Target Position        : {candidate.get('fwd_pos', 'N/A')}

REVERSE PRIMER  (5' -> 3') : {rev_seq}
  - Length                 : {len(rev_seq)} bp
  - Melting Temp (Tm)      : {rev_tm} °C
  - GC Content             : {rev_gc} %
  - Target Position        : {candidate.get('rev_pos', 'N/A')}

AMPLICON PRODUCT SIZE      : {prod_size} bp
TM DIFFERENCE (Fwd - Rev)  : {tm_diff} °C

Thermodynamic & BLAST Audit:
  [QC 1] Melting Temp Range (57-63°C) : {'PASS' if (57 <= fwd_tm <= 63 and 57 <= rev_tm <= 63) else 'FAIL'}
  [QC 2] GC Content Range (40-60%)    : {'PASS' if (40 <= fwd_gc <= 60 and 40 <= rev_gc <= 60) else 'FAIL'}
  [QC 3] GC Clamp 3' End (1-3 G/C)    : Fwd: {fwd_clamp_gc} G/C, Rev: {rev_clamp_gc} G/C -> {'PASS' if (fwd_clamp_pass and rev_clamp_pass) else 'PASS' if (fwd_clamp_gc == 'N/A') else 'FAIL'}
  [QC 4] Tm Difference (≤ 2.0°C)      : {'PASS' if tm_diff <= 2.0 else 'FAIL'}
  [QC 5] BLAST Off-target Hits (≤ 1)  : Fwd: {fwd_blast.get('off_target_hits', 0)} hits, Rev: {rev_blast.get('off_target_hits', 0)} hits -> {'PASS' if (fwd_blast.get('off_target_hits', 0) <= 1 and rev_blast.get('off_target_hits', 0) <= 1) else 'FAIL'}
  [QC 6] Hairpin MFE (> -2.0)         : Fwd: {fwd_struct.get('hairpin_mfe', 'N/A')} kcal/mol, Rev: {rev_struct.get('hairpin_mfe', 'N/A')} kcal/mol -> {'PASS' if (fwd_struct.get('hairpin_pass', True) and rev_struct.get('hairpin_pass', True)) else 'FAIL'}
  [QC 7] Self-Dimer MFE (> -6.0)      : Fwd: {fwd_struct.get('self_dimer_mfe', 'N/A')} kcal/mol, Rev: {rev_struct.get('self_dimer_mfe', 'N/A')} kcal/mol -> {'PASS' if (fwd_struct.get('self_dimer_pass', True) and rev_struct.get('self_dimer_pass', True)) else 'FAIL'}
  [QC 8] Hetero-Dimer MFE (> -6.0)    : {hetero_struct.get('hetero_dimer_mfe', 'N/A')} kcal/mol -> {'PASS' if hetero_struct.get('hetero_dimer_pass', True) else 'FAIL'}

Failure Warnings & Advisories:
"""
        if failures:
            for f_idx, fail in enumerate(failures, 1):
                report += f"  [{f_idx}] {fail}\n"
        else:
            report += "  None. Primer pair passed all acceptance criteria.\n"

        report += f"""
Wet-Lab Experimental Recommendations:
  - Recommended Annealing Temp (Ta) : {rec_ta} °C (Ta = Tm_min - 3°C)
  - Recommended MgCl2 Concentration : 1.5 – 2.5 mM
  - Recommended Primer Concentration : 0.2 – 0.5 µM per reaction
  - Recommended Extension Time      : {max(30, prod_size // 1000 * 60)} seconds
  - Master Mix Suggestion           : Standard Taq 2X Master Mix or High-Fidelity Polymerase
"""

    # Append reasoning trace if available (compact — skip verbose observation steps)
    if reasoning_trace:
        report += """
================================================================================
REACT REASONING TRACE — Agent Decision Log
================================================================================
"""
        for step in reasoning_trace:
            step_type = step.get("type", "unknown")
            # Skip raw observation steps — they contain verbose tool JSON output
            if step_type == "observation":
                tool = step.get("tool_name", "")
                success = step.get("success", True)
                report += f"\n[{step.get('timestamp', '')}] OBSERVATION: {tool} → {'✓ Success' if success else '✗ Failed'}\n"
                continue
            content = step.get("content", "")
            if len(content) > 200:
                content = content[:200] + "..."
            timestamp = step.get("timestamp", "")
            report += f"\n[{timestamp}] {step_type.upper()}:\n{content}\n"

    report += """
================================================================================
Generated by PrimerAgent v2.0 (ReAct + Gemini + Primer3 + Biopython)
Architecture: Single-Agent ReAct with Google Gemini LLM
================================================================================
"""
    return report.strip()
