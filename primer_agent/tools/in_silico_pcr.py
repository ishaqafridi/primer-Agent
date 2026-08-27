"""
Tool 3: In-Silico PCR Tool — Amplicon Prediction & Specificity Gating

Executes in-silico PCR to predict amplicon generation, binding site orientation,
amplicon length, and product multiplicity. Combines UCSC In-Silico PCR for supported
organisms with a local paired-primer sequence engine for custom/reference sequences.

References:
    - UCSC In-Silico PCR: Sanborn et al., Nucleic Acids Res., 2011
    - Primer-BLAST / e-PCR: Schuler, Genome Res., 1997
"""

import re
import json
import urllib.parse
import urllib.request
import logging
import functools
import time
from typing import Dict, Any, List, Optional, Tuple

from langchain_core.tools import tool
from primer_agent.tools.target_resolver import GENOME_ASSEMBLIES

logger = logging.getLogger(__name__)


def reverse_complement(seq: str) -> str:
    """Return reverse complement of a DNA sequence."""
    trans = str.maketrans("ACGTNacgtn", "TGCANtgcan")
    return seq.translate(trans)[::-1]


def _match_primer_sites(primer: str, sequence: str, max_mismatches: int = 2) -> List[int]:
    """Find primer binding positions in sequence allowing up to max_mismatches."""
    p_len = len(primer)
    s_len = len(sequence)
    positions = []

    for i in range(s_len - p_len + 1):
        target_sub = sequence[i:i+p_len]
        mismatches = sum(1 for a, b in zip(primer, target_sub) if a != b)
        if mismatches <= max_mismatches:
            # 3' end mismatch penalty (last 3 bases)
            if primer[-3:] == target_sub[-3:] or mismatches == 0:
                positions.append(i)

    return positions


def _local_in_silico_pcr_impl(
    fwd_primer: str,
    rev_primer: str,
    template_seq: str,
    max_target_distance: int = 1500,
) -> Dict[str, Any]:
    """Local PCR implementation with LRU caching for speed.

    The function now uses an LRU cache to avoid recomputing results for the same
    primer/template combination. This improves performance when the same query
    is run multiple times within a session.
    """
    cache_key = (fwd_primer.upper(), rev_primer.upper(), template_seq.upper(), max_target_distance)
    return _cached_local_pcr_engine(*cache_key)

@functools.lru_cache(maxsize=128)
def _cached_local_pcr_engine(fwd_primer: str, rev_primer: str, template_seq: str, max_target_distance: int) -> Dict[str, Any]:
    """Core logic of the local PCR engine (cached)."""
    # Original implementation logic (unmodified) begins
    fwd = fwd_primer.upper()
    rev = rev_primer.upper()
    seq = template_seq.upper()
    rev_rc = reverse_complement(rev)

    fwd_sites = _match_primer_sites(fwd, seq, max_mismatches=1)
    rev_sites = _match_primer_sites(rev_rc, seq, max_mismatches=1)

    fwd_bound = len(fwd_sites) > 0
    rev_bound = len(rev_sites) > 0

    amplicons = []
    for f_pos in fwd_sites:
        for r_pos in rev_sites:
            if r_pos + len(rev) > f_pos:
                amp_len = (r_pos + len(rev)) - f_pos
                if 40 <= amp_len <= max_target_distance:
                    amp_seq = seq[f_pos:r_pos + len(rev)]
                    amplicons.append({
                        "fwd_start": f_pos,
                        "rev_end": r_pos + len(rev),
                        "amplicon_size": amp_len,
                        "amplicon_sequence": amp_seq[:30] + "..." if len(amp_seq) > 30 else amp_seq,
                        "orientation": "correct",
                    })

    amp_count = len(amplicons)
    # End of original logic
    if amp_count == 1:
        status = "PASS"
        reason = "Single specific PCR amplicon produced."
    elif amp_count == 0:
        status = "FAIL"
        if not fwd_bound and not rev_bound:
            reason = "Neither forward nor reverse primer bound to reference template."
        elif not fwd_bound:
            reason = "Forward primer failed to bind to target template."
        elif not rev_bound:
            reason = "Reverse primer failed to bind to target template."
        else:
            reason = "Primers bound but orientation or distance was invalid (no product)."
    else:
        status = "FAIL"
        reason = f"Multiple potential PCR amplicons detected ({amp_count} products)."

    return {
        "status": status,
        "engine_used": "Local Reference PCR Engine",
        "amplicon_count": amp_count,
        "amplicon_size": amplicons[0]["amplicon_size"] if amplicons else 0,
        "amplicons": amplicons,
        "forward_binding": fwd_bound,
        "reverse_binding": rev_bound,
        "orientation": "correct" if amp_count > 0 else "incorrect/none",
        "target_match": amp_count > 0,
        "specific_product": amp_count == 1,
        "reason": reason,
    }
    """
    Local reference sequence PCR engine.
    Scans template for forward binding sites and reverse complement binding sites.
    """
    fwd = fwd_primer.upper()
    rev = rev_primer.upper()
    seq = template_seq.upper()
    rev_rc = reverse_complement(rev)

    fwd_sites = _match_primer_sites(fwd, seq, max_mismatches=1)
    rev_sites = _match_primer_sites(rev_rc, seq, max_mismatches=1)

    fwd_bound = len(fwd_sites) > 0
    rev_bound = len(rev_sites) > 0

    amplicons = []
    for f_pos in fwd_sites:
        for r_pos in rev_sites:
            if r_pos + len(rev) > f_pos:
                amp_len = (r_pos + len(rev)) - f_pos
                if 40 <= amp_len <= max_target_distance:
                    amp_seq = seq[f_pos:r_pos + len(rev)]
                    amplicons.append({
                        "fwd_start": f_pos,
                        "rev_end": r_pos + len(rev),
                        "amplicon_size": amp_len,
                        "amplicon_sequence": amp_seq[:30] + "..." if len(amp_seq) > 30 else amp_seq,
                        "orientation": "correct",
                    })

    amp_count = len(amplicons)
    fwd_bound_flag = fwd_bound
    rev_bound_flag = rev_bound

    if amp_count == 1:
        status = "PASS"
        reason = "Single specific PCR amplicon produced."
    elif amp_count == 0:
        status = "FAIL"
        if not fwd_bound_flag and not rev_bound_flag:
            reason = "Neither forward nor reverse primer bound to reference template."
        elif not fwd_bound_flag:
            reason = "Forward primer failed to bind to target template."
        elif not rev_bound_flag:
            reason = "Reverse primer failed to bind to target template."
        else:
            reason = "Primers bound but orientation or distance was invalid (no product)."
    else:
        status = "FAIL"
        reason = f"Multiple potential PCR amplicons detected ({amp_count} products)."

    return {
        "status": status,
        "engine_used": "Local Reference PCR Engine",
        "amplicon_count": amp_count,
        "amplicon_size": amplicons[0]["amplicon_size"] if amplicons else 0,
        "amplicons": amplicons,
        "forward_binding": fwd_bound_flag,
        "reverse_binding": rev_bound_flag,
        "orientation": "correct" if amp_count > 0 else "incorrect/none",
        "target_match": amp_count > 0,
        "specific_product": amp_count == 1,
        "reason": reason,
    }


_UCSC_CACHE: Dict[Tuple[str, str, str], Optional[Dict[str, Any]]] = {}


def _ucsc_in_silico_pcr_impl(
    fwd_primer: str,
    rev_primer: str,
    organism: str = "Homo sapiens",
    ucsc_db: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    """Query UCSC In-Silico PCR web service for supported organisms."""
    db = ucsc_db or GENOME_ASSEMBLIES.get(organism, {}).get("ucsc_db")
    if not db or db == "custom":
        return None

    cache_key = (fwd_primer.upper(), rev_primer.upper(), db)
    if cache_key in _UCSC_CACHE:
        return _UCSC_CACHE[cache_key]

    try:
        url = "http://insilico.ehu.es/PCR/"
        data = urllib.parse.urlencode({
            "db": db,
            "wp_pair": f"{fwd_primer} {rev_primer}",
            "Submit": "submit",
        }).encode("utf-8")

        req = urllib.request.Request(url, data=data, headers={"User-Agent": "PrimerAgent/3.0"})
        with urllib.request.urlopen(req, timeout=2.0) as response:
            html = response.read().decode("utf-8")

            # Parse amplicons from UCSC output
            matches = re.findall(r">([\w.:-]+)\s+(\d+)bp\s+([ACGTN]+)", html, re.IGNORECASE)
            amp_count = len(matches)
            amplicons = []

            for m in matches:
                amplicons.append({
                    "target_region": m[0],
                    "amplicon_size": int(m[1]),
                    "sequence_snippet": m[2][:50],
                    "orientation": "correct",
                })

            if amp_count > 0:
                res = {
                    "status": "PASS" if amp_count == 1 else "FAIL",
                    "engine_used": f"UCSC In-Silico PCR ({db})",
                    "amplicon_count": amp_count,
                    "amplicon_size": amplicons[0]["amplicon_size"],
                    "amplicons": amplicons,
                    "forward_binding": True,
                    "reverse_binding": True,
                    "orientation": "correct",
                    "target_match": True,
                    "specific_product": amp_count == 1,
                    "reason": "Single product from UCSC In-Silico PCR" if amp_count == 1 else f"{amp_count} products from UCSC PCR",
                }
                _UCSC_CACHE[cache_key] = res
                return res
    except Exception as e:
        logger.debug(f"UCSC In-Silico PCR query failed or timed out: {e}")

    _UCSC_CACHE[cache_key] = None
    return None


def _run_in_silico_pcr_impl(
    fwd_primer: str,
    rev_primer: str,
    template_seq: Optional[str] = None,
    organism: str = "Homo sapiens",
    target_name: str = "TARGET",
    genome_assembly: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Main entry point for In-Silico PCR validation tool.
    
    1. Attempts UCSC In-Silico PCR if supported and available.
    2. Falls back to Local Reference PCR Engine if template sequence is provided.
    """
    fwd = fwd_primer.strip().upper()
    rev = rev_primer.strip().upper()

    # If template sequence is provided, run local PCR engine first for maximum performance
    if template_seq and template_seq.strip():
        local_res = _local_in_silico_pcr_impl(fwd, rev, template_seq)
        local_res.update({
            "organism": organism,
            "target": target_name,
            "genome": genome_assembly or GENOME_ASSEMBLIES.get(organism, {}).get("assembly", "Reference"),
        })
        return local_res

    # Attempt UCSC for model organisms when template sequence is not provided
    ucsc_res = _ucsc_in_silico_pcr_impl(fwd, rev, organism=organism)
    if ucsc_res is not None:
        ucsc_res.update({
            "organism": organism,
            "target": target_name,
            "genome": genome_assembly or GENOME_ASSEMBLIES.get(organism, {}).get("assembly", "GRCh38"),
        })
        return ucsc_res

    # If neither UCSC nor sequence is available
    return {
        "status": "NOT CHECKED",
        "engine_used": "None",
        "organism": organism,
        "target": target_name,
        "amplicon_count": 0,
        "amplicon_size": 0,
        "amplicons": [],
        "forward_binding": False,
        "reverse_binding": False,
        "orientation": "none",
        "target_match": False,
        "specific_product": False,
        "reason": "Template sequence not provided and UCSC engine unavailable.",
    }


@tool
def in_silico_pcr(
    fwd_primer: str,
    rev_primer: str,
    template_seq: Optional[str] = None,
    organism: str = "Homo sapiens",
    target_name: str = "TARGET",
) -> str:
    """Predict PCR product generation, binding orientation, and amplicon count.
    
    Use this tool after generating primer candidates to perform In-Silico PCR validation.
    It verifies that the primer pair forms a specific PCR product on the target template
    or reference genome (UCSC / Local PCR engine).
    
    Args:
        fwd_primer: Forward primer sequence (5'→3').
        rev_primer: Reverse primer sequence (5'→3').
        template_seq: Optional DNA template sequence string.
        organism: Scientific organism name (default: "Homo sapiens").
        target_name: Target gene symbol or ID.
    
    Returns:
        JSON string with in-silico PCR status, amplicon count, size, orientation, and details.
    """
    result = _run_in_silico_pcr_impl(
        fwd_primer=fwd_primer,
        rev_primer=rev_primer,
        template_seq=template_seq,
        organism=organism,
        target_name=target_name,
    )
    return json.dumps(result, indent=2)
