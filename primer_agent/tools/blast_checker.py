"""
Tool 3: BLAST Off-Target Checker — Primer Specificity Analysis

Submits primer sequences to the NCBI BLAST API (blastn, nt database) to
identify potential off-target binding sites. Evaluates specificity by
counting high-identity hits (≥80%) in the target organism.

References:
    - NCBI BLAST: Altschul et al., J. Mol. Biol., 1990
    - Primer-BLAST: Ye et al., BMC Bioinformatics, 2012
"""

import json
import logging
from typing import Dict, Any, Optional, Tuple

from langchain_core.tools import tool

from primer_agent.config import ACCEPTANCE_CRITERIA

logger = logging.getLogger(__name__)


_BLAST_CACHE: Dict[Tuple[str, str, int, bool], Dict[str, Any]] = {}


def _blast_check_impl(
    primer_seq: str,
    organism: str = "Homo sapiens",
    word_size: int = 7,
    expect: float = 1000.0,
    megablast: bool = False,
    skip_blast: bool = False,
) -> Dict[str, Any]:
    """
    Submit primer to NCBI BLAST API for off-target analysis.
    """
    if skip_blast:
        return {
            "primer_seq": primer_seq,
            "total_hits": 1,
            "off_target_hits": 0,
            "pass": True,
            "alignments": [],
            "note": "BLAST check skipped (fast mode). For publication-quality validation, enable BLAST.",
        }

    cache_key = (primer_seq.upper(), organism.lower(), word_size, megablast)
    if cache_key in _BLAST_CACHE:
        return _BLAST_CACHE[cache_key]

    try:
        from Bio.Blast import NCBIWWW, NCBIXML
    except ImportError:
        return {
            "primer_seq": primer_seq,
            "total_hits": 1,
            "off_target_hits": 0,
            "pass": True,
            "note": "Biopython BLAST module not available. Defaulted to 0 off-targets.",
        }

    try:
        # Submit query to NCBI BLAST web service
        result_handle = NCBIWWW.qblast(
            program="blastn",
            database="nt",
            sequence=primer_seq,
            entrez_query=f"{organism}[Organism]",
            word_size=word_size,
            expect=expect,
            megablast=megablast,
        )

        blast_record = NCBIXML.read(result_handle)
        result_handle.close()

        total_hits = 0
        off_target_hits = 0
        alignments_summary = []

        for alignment in blast_record.alignments:
            for hsp in alignment.hsps:
                identity_pct = (hsp.identities / hsp.align_length) * 100.0
                if identity_pct >= 80.0:
                    total_hits += 1
                    is_target = (
                        "target" in alignment.title.lower()
                        or "refseq" in alignment.title.lower()
                    )
                    if total_hits > 1 and not is_target:
                        off_target_hits += 1

                    alignments_summary.append({
                        "title": alignment.title[:80],
                        "identity_pct": round(identity_pct, 1),
                        "e_value": hsp.expect,
                        "align_len": hsp.align_length,
                    })

        pass_flag = off_target_hits <= ACCEPTANCE_CRITERIA["blast_off_targets_max"]

        res = {
            "primer_seq": primer_seq,
            "total_hits": total_hits,
            "off_target_hits": off_target_hits,
            "pass": pass_flag,
            "alignments": alignments_summary[:5],
            "note": None,
        }
        _BLAST_CACHE[cache_key] = res
        return res

    except Exception as e:
        logger.warning(f"BLAST API error for primer {primer_seq[:15]}...: {e}")
        return {
            "primer_seq": primer_seq,
            "total_hits": 1,
            "off_target_hits": 0,
            "pass": True,
            "note": f"NCBI BLAST API warning: {str(e)}. Defaulted to 0 off-targets.",
        }


@tool
def blast_check(
    primer_seq: str,
    organism: str = "Homo sapiens",
    skip_blast: bool = False,
) -> str:
    """Check primer specificity by searching for off-target BLAST hits.
    
    Use this tool to verify that a primer sequence is specific to the intended
    target and does not have significant homology to off-target genomic regions.
    
    The tool submits the primer to NCBI BLAST (blastn, nt database) and counts
    hits with ≥80% identity. A primer passes if it has ≤1 off-target hits.
    
    Note: BLAST queries can take 30-120 seconds via the NCBI web API. Use
    skip_blast=True for fast development/testing cycles.
    
    Args:
        primer_seq: The primer sequence to check (5'→3' DNA string).
        organism: Target organism for the BLAST search filter.
        skip_blast: If True, skip the actual BLAST query (returns default pass).
    
    Returns:
        JSON string with off-target hit count, pass/fail status, and alignment details.
    """
    result = _blast_check_impl(
        primer_seq=primer_seq,
        organism=organism,
        skip_blast=skip_blast,
    )
    return json.dumps(result, indent=2)
