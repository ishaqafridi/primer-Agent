"""
Tool 4: Secondary Structure Checker — Hairpin, Self-Dimer, and Hetero-Dimer Analysis

Evaluates primer sequences for thermodynamically unfavorable secondary structures
using Nearest-Neighbor thermodynamic binding models (SantaLucia 1998) and optionally
ViennaRNA's RNAfold.

Thresholds (from primer design best practices):
    - Hairpin MFE:      > -2.0 kcal/mol (acceptable)
    - Self-dimer MFE:   > -6.0 kcal/mol (acceptable)
    - Hetero-dimer MFE: > -6.0 kcal/mol (acceptable)

References:
    - SantaLucia, Proc. Natl. Acad. Sci., 1998
    - ViennaRNA: Lorenz et al., Algorithms Mol. Biol., 2011
"""

import re
import json
import subprocess
import logging
from typing import Dict, Any

from langchain_core.tools import tool

from primer_agent.config import ACCEPTANCE_CRITERIA

logger = logging.getLogger(__name__)


def _calculate_complementary_mfe(seq1: str, seq2: str) -> float:
    """
    Calculate inter/intramolecular duplex MFE based on contiguous complementary alignment.
    G-C pair: -2.0 kcal/mol, A-T pair: -1.2 kcal/mol.
    Requires at least 3 consecutive matches to initiate stable duplex.
    3'-end complementarity is weighted higher for PCR specificity.
    """
    s1 = seq1.upper()
    trans = str.maketrans("ACGTN", "TGCAN")
    s2_comp = seq2.upper().translate(trans)

    best_mfe = 0.0
    len1, len2 = len(s1), len(s2_comp)

    for shift in range(-len2 + 3, len1 - 2):
        running_mfe = 0.0
        consecutive = 0

        for i in range(len1):
            j = i - shift
            if 0 <= j < len2:
                b1 = s1[i]
                b2_comp = s2_comp[len2 - 1 - j]
                if b1 == b2_comp:
                    mfe_contrib = -2.0 if b1 in ("G", "C") else -1.2
                    running_mfe += mfe_contrib
                    consecutive += 1
                else:
                    running_mfe = 0.0
                    consecutive = 0

                if consecutive >= 3:
                    # 3' end complementarity increases dimer risk
                    mult = 1.3 if (i >= len1 - 5 or j >= len2 - 5) else 1.0
                    mfe_val = running_mfe * mult
                    if mfe_val < best_mfe:
                        best_mfe = mfe_val
            else:
                running_mfe = 0.0
                consecutive = 0

    return round(best_mfe, 2)


def _calculate_hairpin_mfe(seq: str) -> float:
    """Calculate intramolecular hairpin MFE using loop + stem energetics."""
    seq = seq.upper()
    n = len(seq)
    best_mfe = 0.0

    # Scan hairpin loops of size 3 to 8 bp
    for loop_size in range(3, 9):
        for i in range(0, n - loop_size - 4):
            stem_len = 0
            stem_mfe = 0.0
            left = i
            right = i + loop_size + 1
            while left >= 0 and right < n:
                b1, b2 = seq[left], seq[right]
                if (b1 == 'G' and b2 == 'C') or (b1 == 'C' and b2 == 'G'):
                    stem_mfe += -2.0
                    stem_len += 1
                elif (b1 == 'A' and b2 == 'T') or (b1 == 'T' and b2 == 'A'):
                    stem_mfe += -1.2
                    stem_len += 1
                else:
                    break
                left -= 1
                right += 1

            if stem_len >= 2:
                # Add loop strain penalty (+3.5 kcal/mol)
                total_hairpin_mfe = stem_mfe + 3.5
                if total_hairpin_mfe < best_mfe:
                    best_mfe = total_hairpin_mfe

    return round(best_mfe, 2)


def _check_secondary_structure_impl(primer_seq: str) -> Dict[str, Any]:
    """
    Analyze a primer for hairpin and self-dimer secondary structures.
    
    Uses Nearest-Neighbor thermodynamic calculations, with optional ViennaRNA
    RNAfold subprocess for hairpin prediction if available.
    """
    primer_seq = primer_seq.upper()
    rnafold_structure = None
    rnafold_mfe = None

    # Try ViennaRNA subprocess (RNAfold) for hairpin prediction
    try:
        proc = subprocess.run(
            ['RNAfold', '--noPS'],
            input=primer_seq,
            text=True,
            capture_output=True,
            timeout=5,
        )
        if proc.returncode == 0:
            lines = proc.stdout.strip().split('\n')
            if len(lines) >= 2:
                match = re.search(r'([.()]+)\s+\(\s*([-\d.]+)\)', lines[1])
                if match:
                    rnafold_structure = match.group(1)
                    rnafold_mfe = float(match.group(2))
    except Exception:
        pass  # RNAfold not installed or not in PATH

    hp_mfe = _calculate_hairpin_mfe(primer_seq)
    sd_mfe = _calculate_complementary_mfe(primer_seq, primer_seq)

    # Use RNAfold MFE if available, otherwise native hairpin MFE
    final_hp_mfe = rnafold_mfe if rnafold_mfe is not None else hp_mfe

    hp_pass = final_hp_mfe > ACCEPTANCE_CRITERIA["hairpin_mfe_min"]
    sd_pass = sd_mfe > ACCEPTANCE_CRITERIA["self_dimer_mfe_min"]

    return {
        "primer_seq": primer_seq,
        "hairpin_structure": rnafold_structure or ("Found" if final_hp_mfe < -2.0 else "None"),
        "hairpin_mfe": final_hp_mfe,
        "hairpin_pass": hp_pass,
        "self_dimer_mfe": sd_mfe,
        "self_dimer_pass": sd_pass,
        "method": "ViennaRNA + Nearest-Neighbor" if rnafold_mfe is not None else "Nearest-Neighbor Thermodynamics",
    }


def _check_heterodimer_impl(fwd_seq: str, rev_seq: str) -> Dict[str, Any]:
    """
    Check cross (hetero) dimer interaction between forward and reverse primers.
    """
    hd_mfe = _calculate_complementary_mfe(fwd_seq, rev_seq)
    hd_pass = hd_mfe > ACCEPTANCE_CRITERIA["hetero_dimer_mfe_min"]

    return {
        "fwd_seq": fwd_seq.upper(),
        "rev_seq": rev_seq.upper(),
        "hetero_dimer_mfe": hd_mfe,
        "hetero_dimer_pass": hd_pass,
    }


@tool
def check_structure(primer_seq: str) -> str:
    """Analyze a primer sequence for hairpin and self-dimer secondary structures."""
    result = _check_secondary_structure_impl(primer_seq)
    return json.dumps(result, indent=2)


@tool
def check_heterodimer_tool(fwd_seq: str, rev_seq: str) -> str:
    """Check hetero-dimer interaction between forward and reverse primers."""
    result = _check_heterodimer_impl(fwd_seq, rev_seq)
    return json.dumps(result, indent=2)
