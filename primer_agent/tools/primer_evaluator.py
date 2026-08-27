"""
Tool 6: Primer Evaluator — Multi-Criteria Quality Scoring System (v3.0)

Scores primer pairs on a 0-100 scale using multi-gate validation and weighted criteria
covering In-Silico PCR (Gate 2), thermodynamic properties, specificity, and structural stability.

Scoring Breakdown (total = 100):
    - In-Silico PCR & Amplicon Validation (Gate 2): 25 pts
    - Specificity / BLAST:                         20 pts
    - Tm range (57-63°C) & ΔTm:                     20 pts
    - GC range (40-60%) & 3' Clamp:                 15 pts
    - Secondary Structure (Hairpin & Self-dimer):   10 pts
    - Hetero-dimer Stability:                       5 pts
    - Exon / Transcript Compatibility:               5 pts

References:
    - Primer design guidelines: Dieffenbach et al., PCR Methods Appl., 1993
    - qPCR primer criteria: Bustin et al., Clinical Chemistry, 2009
"""

import json
import logging
from typing import Dict, Any, List, Tuple, Optional

from langchain_core.tools import tool
from primer_agent.config import ACCEPTANCE_CRITERIA, SCORING_WEIGHTS

logger = logging.getLogger(__name__)


def _check_gc_clamp(seq: str) -> Tuple[int, bool]:
    """Check the 3' end of a primer for a GC clamp (1-3 G/C in last 5 bp)."""
    if not seq or len(seq) < 5:
        return 0, False
    end_5 = seq[-5:].upper()
    gc_count = end_5.count('G') + end_5.count('C')
    min_clamp = ACCEPTANCE_CRITERIA.get("gc_clamp_min", 1)
    max_clamp = ACCEPTANCE_CRITERIA.get("gc_clamp_max", 3)
    is_passed = min_clamp <= gc_count <= max_clamp
    return gc_count, is_passed


def _evaluate_primer_pair_impl(
    candidate: Dict[str, Any],
    fwd_blast: Dict[str, Any],
    rev_blast: Dict[str, Any],
    fwd_struct: Dict[str, Any],
    rev_struct: Dict[str, Any],
    hetero_struct: Dict[str, Any],
    pcr_result: Optional[Dict[str, Any]] = None,
    exon_result: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Strict Validation-First Primer Pair Evaluation.

    WORKFLOW: VALIDATE → REJECT FAILURES → SCORE PASSING PAIRS

    Step 1: Run ALL critical QC checks and collect failures.
    Step 2: If ANY critical check fails → STATUS=FAIL, SCORE=None (NOT SCORED),
            RECOMMENDED=False, EXCLUDE FROM FINAL RESULTS.
    Step 3: Only candidates passing ALL critical checks get a numerical score (60-100).
    """
    failures = []
    fwd_seq = candidate.get("fwd_seq", "")
    rev_seq = candidate.get("rev_seq", "")

    # ══════════════════════════════════════════════════════════════════════════
    # PHASE 1: STRICT QC VALIDATION (all checks run, failures collected)
    # ══════════════════════════════════════════════════════════════════════════

    # --- QC 1: In-Silico PCR (must produce exactly 1 intended amplicon) ---
    pcr_gate_pass = True
    if pcr_result:
        pcr_status = pcr_result.get("status", "FAIL")
        amp_count = pcr_result.get("amplicon_count", 0)
        pcr_reason = pcr_result.get("reason", "In-Silico PCR failed.")
        if pcr_status != "PASS" or amp_count != 1:
            pcr_gate_pass = False
            failures.append(f"CRITICAL: In-Silico PCR failed — {pcr_reason} (amplicon_count={amp_count}).")

    # --- QC 2: Tm Range (57–63°C) & ΔTm (≤ 2°C) ---
    tm_min, tm_max = ACCEPTANCE_CRITERIA["tm_min"], ACCEPTANCE_CRITERIA["tm_max"]
    fwd_tm = candidate.get("fwd_tm", 60.0)
    rev_tm = candidate.get("rev_tm", 60.0)
    tm_diff = candidate.get("tm_diff", abs(fwd_tm - rev_tm))
    tm_pass = True
    if not (tm_min <= fwd_tm <= tm_max):
        failures.append(f"CRITICAL: Forward Tm ({fwd_tm}°C) outside {tm_min}–{tm_max}°C.")
        tm_pass = False
    if not (tm_min <= rev_tm <= tm_max):
        failures.append(f"CRITICAL: Reverse Tm ({rev_tm}°C) outside {tm_min}–{tm_max}°C.")
        tm_pass = False
    if tm_diff > ACCEPTANCE_CRITERIA["tm_diff_max"]:
        failures.append(f"CRITICAL: ΔTm ({tm_diff}°C) exceeds {ACCEPTANCE_CRITERIA['tm_diff_max']}°C limit.")
        tm_pass = False

    # --- QC 3: GC% Range (40–60%) & 3' GC Clamp ---
    gc_min, gc_max = ACCEPTANCE_CRITERIA["gc_min"], ACCEPTANCE_CRITERIA["gc_max"]
    fwd_gc = candidate.get("fwd_gc", 50.0)
    rev_gc = candidate.get("rev_gc", 50.0)
    fwd_clamp_gc, fwd_clamp_pass = _check_gc_clamp(fwd_seq)
    rev_clamp_gc, rev_clamp_pass = _check_gc_clamp(rev_seq)
    gc_pass = True
    if not (gc_min <= fwd_gc <= gc_max):
        failures.append(f"CRITICAL: Forward GC ({fwd_gc}%) outside {gc_min}–{gc_max}%.")
        gc_pass = False
    if not (gc_min <= rev_gc <= gc_max):
        failures.append(f"CRITICAL: Reverse GC ({rev_gc}%) outside {gc_min}–{gc_max}%.")
        gc_pass = False
    if not fwd_clamp_pass:
        failures.append(f"CRITICAL: Forward 3' GC clamp failed ({fwd_clamp_gc} G/C in last 5bp).")
        gc_pass = False
    if not rev_clamp_pass:
        failures.append(f"CRITICAL: Reverse 3' GC clamp failed ({rev_clamp_gc} G/C in last 5bp).")
        gc_pass = False

    # --- QC 4: Hairpin & Self-Dimer ---
    fwd_hp_pass = fwd_struct.get("hairpin_pass", True)
    rev_hp_pass = rev_struct.get("hairpin_pass", True)
    fwd_sd_pass = fwd_struct.get("self_dimer_pass", True)
    rev_sd_pass = rev_struct.get("self_dimer_pass", True)
    structure_pass = True
    if not fwd_hp_pass:
        failures.append(f"CRITICAL: Forward hairpin MFE ({fwd_struct.get('hairpin_mfe', 'N/A')} kcal/mol) ≤ {ACCEPTANCE_CRITERIA['hairpin_mfe_min']}.")
        structure_pass = False
    if not rev_hp_pass:
        failures.append(f"CRITICAL: Reverse hairpin MFE ({rev_struct.get('hairpin_mfe', 'N/A')} kcal/mol) ≤ {ACCEPTANCE_CRITERIA['hairpin_mfe_min']}.")
        structure_pass = False
    if not fwd_sd_pass:
        failures.append(f"CRITICAL: Forward self-dimer MFE ({fwd_struct.get('self_dimer_mfe', 'N/A')} kcal/mol) ≤ {ACCEPTANCE_CRITERIA['self_dimer_mfe_min']}.")
        structure_pass = False
    if not rev_sd_pass:
        failures.append(f"CRITICAL: Reverse self-dimer MFE ({rev_struct.get('self_dimer_mfe', 'N/A')} kcal/mol) ≤ {ACCEPTANCE_CRITERIA['self_dimer_mfe_min']}.")
        structure_pass = False

    # --- QC 5: Hetero-Dimer ---
    hd_pass = hetero_struct.get("hetero_dimer_pass", True)
    if not hd_pass:
        failures.append(f"CRITICAL: Hetero-dimer MFE ({hetero_struct.get('hetero_dimer_mfe', 'N/A')} kcal/mol) ≤ {ACCEPTANCE_CRITERIA['hetero_dimer_mfe_min']}.")

    # --- QC 6: BLAST specificity (off-target pair amplification) ---
    fwd_off = fwd_blast.get("off_target_hits", 0)
    rev_off = rev_blast.get("off_target_hits", 0)
    blast_pass = True
    if fwd_off > 1:
        failures.append(f"CRITICAL: Forward primer has {fwd_off} off-target BLAST hits.")
        blast_pass = False
    if rev_off > 1:
        failures.append(f"CRITICAL: Reverse primer has {rev_off} off-target BLAST hits.")
        blast_pass = False

    # ══════════════════════════════════════════════════════════════════════════
    # PHASE 2: REJECT / ELIGIBLE DECISION
    # ══════════════════════════════════════════════════════════════════════════

    all_critical_pass = (
        pcr_gate_pass and tm_pass and gc_pass and
        structure_pass and hd_pass and blast_pass
    )

    if not all_critical_pass:
        # ── FAIL: Any critical QC check failed ──
        # STATUS = FAIL, RECOMMENDED = FALSE, SCORE = NOT SCORED
        # EXCLUDE FROM FINAL RESULTS
        return {
            "candidate": candidate,
            "score": None,              # NOT SCORED — no numerical score for failures
            "pass": False,
            "status": "FAIL",
            "recommended": False,
            "breakdown": None,          # Not scored
            "failures": failures,
            "fwd_blast": fwd_blast,
            "rev_blast": rev_blast,
            "fwd_struct": fwd_struct,
            "rev_struct": rev_struct,
            "hetero_struct": hetero_struct,
            "pcr_result": pcr_result,
            "exon_result": exon_result,
            "fwd_gc_clamp": {"gc_count": fwd_clamp_gc, "pass": fwd_clamp_pass},
            "rev_gc_clamp": {"gc_count": rev_clamp_gc, "pass": rev_clamp_pass},
        }

    # ══════════════════════════════════════════════════════════════════════════
    # PHASE 3: SCORE ONLY PASSING CANDIDATES (60–100 range)
    # ══════════════════════════════════════════════════════════════════════════

    breakdown = {}

    # In-Silico PCR (25 pts)
    breakdown["in_silico_pcr_pts"] = SCORING_WEIGHTS.get("in_silico_pcr", 25)

    # Tm Range & ΔTm (20 pts) — already validated as pass
    tm_pts = SCORING_WEIGHTS["tm_range"]
    # Slight deduction for deviation from optimal 60°C
    fwd_dev = abs(fwd_tm - 60.0)
    rev_dev = abs(rev_tm - 60.0)
    if fwd_dev > 1.0 or rev_dev > 1.0 or tm_diff > 1.0:
        tm_pts = max(14, tm_pts - int(fwd_dev) - int(rev_dev) - int(tm_diff * 2))
    breakdown["tm_pts"] = tm_pts

    # GC Range & 3' Clamp (15 pts) — already validated as pass
    gc_pts = SCORING_WEIGHTS["gc_range"]
    fwd_gc_dev = abs(fwd_gc - 50.0)
    rev_gc_dev = abs(rev_gc - 50.0)
    if fwd_gc_dev > 5.0 or rev_gc_dev > 5.0:
        gc_pts = max(10, gc_pts - int(fwd_gc_dev * 0.3) - int(rev_gc_dev * 0.3))
    breakdown["gc_pts"] = gc_pts

    # BLAST specificity (20 pts) — already validated as pass
    blast_pts = SCORING_WEIGHTS["blast_specificity"]
    if fwd_off == 1 or rev_off == 1:
        blast_pts = max(14, blast_pts - (fwd_off + rev_off) * 3)
    breakdown["blast_pts"] = blast_pts

    # Structure (10 pts) — already validated as pass
    breakdown["structure_pts"] = SCORING_WEIGHTS["hairpin_stability"]

    # Dimer (5 pts) — already validated as pass
    breakdown["dimer_pts"] = 5

    # Exon / Transcript (5 pts)
    exon_pts = 5
    if exon_result:
        exon_pts = 5 if exon_result.get("exon_junction") else 3
    breakdown["exon_pts"] = exon_pts

    total_score = max(60.0, min(100.0, float(sum(breakdown.values()))))

    return {
        "candidate": candidate,
        "score": round(total_score, 1),
        "pass": True,
        "status": "PASS",
        "recommended": True,
        "breakdown": breakdown,
        "failures": [],              # No failures for passing candidates
        "fwd_blast": fwd_blast,
        "rev_blast": rev_blast,
        "fwd_struct": fwd_struct,
        "rev_struct": rev_struct,
        "hetero_struct": hetero_struct,
        "pcr_result": pcr_result,
        "exon_result": exon_result,
        "fwd_gc_clamp": {"gc_count": fwd_clamp_gc, "pass": fwd_clamp_pass},
        "rev_gc_clamp": {"gc_count": rev_clamp_gc, "pass": rev_clamp_pass},
    }


@tool
def evaluate_primers(
    fwd_seq: str,
    rev_seq: str,
    fwd_tm: float,
    rev_tm: float,
    fwd_gc: float,
    rev_gc: float,
    product_size: int,
    fwd_blast_off_targets: int = 0,
    rev_blast_off_targets: int = 0,
    fwd_hairpin_mfe: float = 0.0,
    rev_hairpin_mfe: float = 0.0,
    fwd_self_dimer_mfe: float = 0.0,
    rev_self_dimer_mfe: float = 0.0,
    hetero_dimer_mfe: float = 0.0,
    pcr_status: str = "PASS",
    pcr_amplicon_count: int = 1,
) -> str:
    """Evaluate a primer pair using the multi-gate quality scoring system (0-100 scale).
    
    Use this tool after running in_silico_pcr, BLAST, and structure checks.
    Computes quality score out of 100 and enforces Gate 2 (In-Silico PCR).
    
    Args:
        fwd_seq: Forward primer sequence.
        rev_seq: Reverse primer sequence.
        fwd_tm: Forward primer melting temperature (°C).
        rev_tm: Reverse primer melting temperature (°C).
        fwd_gc: Forward primer GC content (%).
        rev_gc: Reverse primer GC content (%).
        product_size: Amplicon product size (bp).
        fwd_blast_off_targets: Number of forward primer off-target BLAST hits.
        rev_blast_off_targets: Number of reverse primer off-target BLAST hits.
        fwd_hairpin_mfe: Forward primer hairpin MFE (kcal/mol).
        rev_hairpin_mfe: Reverse primer hairpin MFE (kcal/mol).
        fwd_self_dimer_mfe: Forward primer self-dimer MFE (kcal/mol).
        rev_self_dimer_mfe: Reverse primer self-dimer MFE (kcal/mol).
        hetero_dimer_mfe: Hetero-dimer MFE between fwd and rev (kcal/mol).
        pcr_status: Status string from in_silico_pcr ("PASS" or "FAIL").
        pcr_amplicon_count: Number of PCR products predicted.
    
    Returns:
        JSON string with quality score, pass/fail status, breakdown, and failure details.
    """
    candidate = {
        "fwd_seq": fwd_seq,
        "rev_seq": rev_seq,
        "fwd_tm": fwd_tm,
        "rev_tm": rev_tm,
        "tm_diff": round(abs(fwd_tm - rev_tm), 2),
        "fwd_gc": fwd_gc,
        "rev_gc": rev_gc,
        "fwd_len": len(fwd_seq),
        "rev_len": len(rev_seq),
        "product_size": product_size,
    }

    fwd_blast = {"off_target_hits": fwd_blast_off_targets, "pass": fwd_blast_off_targets <= 1}
    rev_blast = {"off_target_hits": rev_blast_off_targets, "pass": rev_blast_off_targets <= 1}
    fwd_struct = {
        "hairpin_mfe": fwd_hairpin_mfe,
        "hairpin_pass": fwd_hairpin_mfe > ACCEPTANCE_CRITERIA["hairpin_mfe_min"],
        "self_dimer_mfe": fwd_self_dimer_mfe,
        "self_dimer_pass": fwd_self_dimer_mfe > ACCEPTANCE_CRITERIA["self_dimer_mfe_min"],
    }
    rev_struct = {
        "hairpin_mfe": rev_hairpin_mfe,
        "hairpin_pass": rev_hairpin_mfe > ACCEPTANCE_CRITERIA["hairpin_mfe_min"],
        "self_dimer_mfe": rev_self_dimer_mfe,
        "self_dimer_pass": rev_self_dimer_mfe > ACCEPTANCE_CRITERIA["self_dimer_mfe_min"],
    }
    hetero_struct = {
        "hetero_dimer_mfe": hetero_dimer_mfe,
        "hetero_dimer_pass": hetero_dimer_mfe > ACCEPTANCE_CRITERIA["hetero_dimer_mfe_min"],
    }
    pcr_res = {
        "status": pcr_status,
        "amplicon_count": pcr_amplicon_count,
        "amplicon_size": product_size,
        "reason": "OK" if pcr_status == "PASS" else "Failed In-Silico PCR gate",
    }

    result = _evaluate_primer_pair_impl(
        candidate=candidate,
        fwd_blast=fwd_blast,
        rev_blast=rev_blast,
        fwd_struct=fwd_struct,
        rev_struct=rev_struct,
        hetero_struct=hetero_struct,
        pcr_result=pcr_res,
    )

    return json.dumps({
        "score": result["score"],
        "pass": result["pass"],
        "breakdown": result["breakdown"],
        "failures": result["failures"],
        "candidate": candidate,
    }, indent=2)
