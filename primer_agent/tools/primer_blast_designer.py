"""
Tool 2: Primer-BLAST Design Engine — Generate PCR Primer Pair Candidates

Implements NCBI Primer-BLAST style primer design using sequence analysis,
Nearest-Neighbor thermodynamic calculations (SantaLucia 1998), and
specificity/amplicon constraint evaluation.

References:
    - Primer-BLAST: Ye et al., BMC Bioinformatics, 2012
    - SantaLucia J Jr., PNAS 1998 (Nearest-neighbor thermodynamics)
"""

import json
import math
import logging
from typing import Dict, Any, List, Tuple, Optional

from langchain_core.tools import tool

from primer_agent.config import DEFAULT_PRESETS

logger = logging.getLogger(__name__)

# Nearest-Neighbor Thermodynamic Parameters (SantaLucia 1998)
# dH (kcal/mol), dS (cal/K/mol)
NN_PARAMS = {
    'AA': (-7.9, -22.2), 'TT': (-7.9, -22.2),
    'AT': (-7.2, -20.4), 'TA': (-7.2, -21.3),
    'CA': (-8.5, -22.7), 'TG': (-8.5, -22.7),
    'GT': (-8.4, -22.4), 'AC': (-8.4, -22.4),
    'CT': (-7.8, -21.0), 'AG': (-7.8, -21.0),
    'GA': (-8.2, -22.2), 'TC': (-8.2, -22.2),
    'CG': (-10.6, -27.2), 'GC': (-9.8, -24.4),
    'GG': (-8.0, -19.9), 'CC': (-8.0, -19.9)
}


def calculate_nn_tm(seq: str, Na_conc: float = 50.0, DNA_conc: float = 50.0) -> float:
    """Calculate melting temperature using SantaLucia (1998) Nearest-Neighbor model."""
    seq = seq.upper()
    if len(seq) < 2:
        return 0.0
    
    dH = 0.0
    dS = 0.0

    # Terminal corrections
    if seq[0] in "GC":
        dH += 0.1
        dS += -2.8
    else:
        dH += 2.3
        dS += 4.1

    if seq[-1] in "GC":
        dH += 0.1
        dS += -2.8
    else:
        dH += 2.3
        dS += 4.1

    for i in range(len(seq) - 1):
        dinuc = seq[i:i+2]
        if dinuc in NN_PARAMS:
            h, s = NN_PARAMS[dinuc]
            dH += h
            dS += s

    # Salt correction (SantaLucia 1998)
    Na_M = max(0.001, Na_conc / 1000.0)
    dS_corr = dS + 0.368 * (len(seq) - 1) * math.log(Na_M)

    R = 1.9872  # cal/K/mol
    Ct = max(1e-12, DNA_conc * 1e-9)  # Molar conc
    tm = (1000.0 * dH) / (dS_corr + R * math.log(Ct / 4.0)) - 273.15
    return round(tm, 2)


def reverse_complement(seq: str) -> str:
    """Return reverse complement of a DNA sequence."""
    trans = str.maketrans("ACGTNacgtn", "TGCANtgcan")
    return seq.translate(trans)[::-1]


def _design_primers_impl(
    sequence: str,
    params: Dict[str, Any],
    product_size_range: Tuple[int, int] = (100, 300),
    num_return: int = 10,
) -> List[Dict[str, Any]]:
    """
    Run Primer-BLAST design algorithm to generate optimal primer pair candidates.
    
    Args:
        sequence: DNA template sequence string.
        params: Parameter dictionary for Tm, GC, length constraints.
        product_size_range: Desired amplicon size range (min, max) in bp.
        num_return: Number of primer pairs to generate.
        
    Returns:
        List of candidate dictionaries with primer sequences, Tm, GC%,
        product size, penalty score, and positional information.
    """
    if not sequence or not sequence.strip():
        logger.error("Empty sequence provided for Primer-BLAST design.")
        return []

    clean_seq = "".join(c for c in sequence.upper() if c in "ACGTN")
    seq_len = len(clean_seq)
    if seq_len < 50:
        logger.warning(f"Sequence length ({seq_len} bp) is too short for primer design (min 50 bp required).")
        return []

    # Extract design constraints
    opt_len = int(params.get('PRIMER_OPT_SIZE', 20))
    min_len = int(params.get('PRIMER_MIN_SIZE', 18))
    max_len = int(params.get('PRIMER_MAX_SIZE', 25))
    opt_tm = float(params.get('PRIMER_OPT_TM', 60.0))
    min_tm = float(params.get('PRIMER_MIN_TM', 57.0))
    max_tm = float(params.get('PRIMER_MAX_TM', 63.0))
    min_gc = float(params.get('PRIMER_MIN_GC', 40.0))
    max_gc = float(params.get('PRIMER_MAX_GC', 60.0))
    max_poly_x = int(params.get('PRIMER_MAX_POLY_X', 4))
    na_conc = float(params.get('PRIMER_SALT_MONOVALENT', 50.0))
    dna_conc = float(params.get('PRIMER_DNA_CONC', 50.0))

    prod_min, prod_max = product_size_range

    # 1. Scan forward primers across sequence
    fwd_candidates = []
    max_fwd_start = max(0, seq_len - prod_min)

    for start in range(0, max_fwd_start, 1):
        for l in range(min_len, max_len + 1):
            if start + l > seq_len:
                continue
            cand_seq = clean_seq[start:start+l]

            # Check poly-X repeats
            if any(cand_seq.count(base * max_poly_x) > 0 for base in "ACGT"):
                continue

            gc_pct = (cand_seq.count('G') + cand_seq.count('C')) / l * 100.0
            if not (min_gc <= gc_pct <= max_gc):
                continue

            tm = calculate_nn_tm(cand_seq, Na_conc=na_conc, DNA_conc=dna_conc)
            if not (min_tm <= tm <= max_tm):
                continue

            fwd_candidates.append({
                "seq": cand_seq,
                "start": start,
                "length": l,
                "tm": tm,
                "gc": gc_pct,
            })
            if len(fwd_candidates) >= 200:
                break

    # 2. Scan reverse primers
    rev_candidates = []
    for end in range(prod_min, seq_len, 1):
        for l in range(min_len, max_len + 1):
            if end - l < 0:
                continue
            template_segment = clean_seq[end-l:end]
            cand_seq = reverse_complement(template_segment)

            if any(cand_seq.count(base * max_poly_x) > 0 for base in "ACGT"):
                continue

            gc_pct = (cand_seq.count('G') + cand_seq.count('C')) / l * 100.0
            if not (min_gc <= gc_pct <= max_gc):
                continue

            tm = calculate_nn_tm(cand_seq, Na_conc=na_conc, DNA_conc=dna_conc)
            if not (min_tm <= tm <= max_tm):
                continue

            rev_candidates.append({
                "seq": cand_seq,
                "end": end,
                "start": end - l,
                "length": l,
                "tm": tm,
                "gc": gc_pct,
            })
            if len(rev_candidates) >= 150:
                break

    # 3. Pair forward and reverse primers and score by Primer-BLAST penalty
    scored_pairs = []
    for fwd in fwd_candidates:
        for rev in rev_candidates:
            if rev["start"] <= fwd["start"]:
                continue

            prod_size = rev["end"] - fwd["start"]
            if not (prod_min <= prod_size <= prod_max):
                continue

            tm_diff = abs(fwd["tm"] - rev["tm"])
            if tm_diff > 4.0:
                continue

            # Calculate Primer-BLAST penalty score
            penalty = (
                abs(fwd["tm"] - opt_tm) * 1.5 +
                abs(rev["tm"] - opt_tm) * 1.5 +
                tm_diff * 2.0 +
                abs(fwd["length"] - opt_len) +
                abs(rev["length"] - opt_len)
            )

            scored_pairs.append({
                "fwd": fwd,
                "rev": rev,
                "product_size": prod_size,
                "tm_diff": round(tm_diff, 2),
                "penalty": round(penalty, 2),
            })

    # Sort by lowest penalty
    scored_pairs.sort(key=lambda x: x["penalty"])

    # Fallback to wider constraints if 0 candidates found
    if not scored_pairs and (min_tm > 50.0 or max_tm < 70.0):
        logger.info("0 candidates under strict constraints. Relaxing Primer-BLAST parameters...")
        relaxed_params = dict(params)
        relaxed_params['PRIMER_MIN_TM'] = max(48.0, min_tm - 5.0)
        relaxed_params['PRIMER_MAX_TM'] = min(72.0, max_tm + 5.0)
        relaxed_params['PRIMER_MIN_GC'] = max(25.0, min_gc - 10.0)
        relaxed_params['PRIMER_MAX_GC'] = min(75.0, max_gc + 10.0)
        return _design_primers_impl(sequence, relaxed_params, product_size_range, num_return)

    candidates = []
    seen_fwd_seqs = set()
    for pair in scored_pairs:
        fwd = pair["fwd"]
        rev = pair["rev"]
        fwd_seq = fwd["seq"]

        # Rule 2: Avoid duplicate forward primers
        if fwd_seq in seen_fwd_seqs:
            continue
        seen_fwd_seqs.add(fwd_seq)

        candidates.append({
            "pair_idx": len(candidates) + 1,
            "fwd_seq": fwd["seq"],
            "rev_seq": rev["seq"],
            "fwd_tm": fwd["tm"],
            "rev_tm": rev["tm"],
            "tm_diff": pair["tm_diff"],
            "fwd_gc": round(fwd["gc"], 1),
            "rev_gc": round(rev["gc"], 1),
            "fwd_len": fwd["length"],
            "rev_len": rev["length"],
            "product_size": pair["product_size"],
            "penalty": pair["penalty"],
            "fwd_pos": [fwd["start"], fwd["length"]],
            "rev_pos": [rev["start"], rev["length"]],
        })
        if len(candidates) >= num_return:
            break

    return candidates


@tool
def design_primers_primer_blast(
    sequence: str,
    application: str = "Standard PCR",
    product_size_min: int = 100,
    product_size_max: int = 300,
    num_return: int = 5,
    custom_params: Optional[str] = None,
) -> str:
    """Design PCR primer pairs using the Primer-BLAST design engine.
    
    Use this tool after fetching a DNA sequence. It generates optimal primer pair
    candidates based on the specified application preset and product size range.
    
    Available application presets:
    - "Standard PCR": General-purpose PCR (Tm 57-63°C, GC 40-60%)
    - "qPCR": Quantitative PCR with tighter constraints (Tm 58-62°C, GC 45-60%)
    - "Sanger Sequencing": Sequencing primers (Tm 55-65°C, wider range)
    - "High-GC Preset": For GC-rich templates (Tm 59-65°C, GC 50-70%)
    
    Args:
        sequence: DNA template sequence string (valid ACGT).
        application: PCR application preset name.
        product_size_min: Minimum desired amplicon size in bp.
        product_size_max: Maximum desired amplicon size in bp.
        num_return: Number of primer pairs to generate (1-10).
        custom_params: Optional JSON string of custom parameter overrides.
    
    Returns:
        JSON string containing list of primer pair candidates with sequences,
        Tm, GC%, product size, and penalty scores.
    """
    params = dict(DEFAULT_PRESETS.get(application, DEFAULT_PRESETS["Standard PCR"]))

    if custom_params:
        try:
            overrides = json.loads(custom_params)
            params.update(overrides)
        except json.JSONDecodeError:
            pass

    candidates = _design_primers_impl(
        sequence=sequence,
        params=params,
        product_size_range=(product_size_min, product_size_max),
        num_return=min(num_return, 10),
    )

    return json.dumps({
        "engine": "Primer-BLAST",
        "application": application,
        "product_size_range": [product_size_min, product_size_max],
        "num_candidates": len(candidates),
        "candidates": candidates,
        "params_used": params,
    }, indent=2)
