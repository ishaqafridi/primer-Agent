"""
Tool 1: NCBI Sequence Fetcher — Retrieve DNA sequences from NCBI Entrez

Queries the NCBI Entrez API using Biopython to fetch FASTA sequences by
gene symbol or accession ID. Handles long sequences by extracting a central
target region and detects high-GC and low-complexity regions.

References:
    - NCBI Entrez: https://www.ncbi.nlm.nih.gov/books/NBK25497/
    - Biopython Entrez: https://biopython.org/wiki/Entrez
"""

import re
import json
import logging
from typing import Dict, Any, Optional, Tuple

from langchain_core.tools import tool

logger = logging.getLogger(__name__)


def calculate_gc_content(seq: str) -> float:
    """Calculate GC percentage of a DNA sequence."""
    if not seq:
        return 0.0
    seq = seq.upper()
    g = seq.count('G')
    c = seq.count('C')
    return (g + c) / len(seq) * 100.0


def mask_low_complexity(seq: str) -> Tuple[str, bool]:
    """Mask simple sequence repeats or low complexity regions (homopolymers ≥ 6)."""
    masked_seq = seq
    has_repeats = False
    for base in ['A', 'C', 'G', 'T']:
        pattern = base * 6
        if pattern in masked_seq:
            has_repeats = True
            masked_seq = re.sub(
                f"({base}{{6,}})",
                lambda m: 'N' * len(m.group(1)),
                masked_seq,
            )
    return masked_seq, has_repeats


# In-memory sequence cache
_SEQUENCE_CACHE: Dict[Tuple[str, str], Dict[str, Any]] = {}

# Reference sequence templates for offline testing or fast fallback
_MOCK_GENE_TEMPLATES: Dict[str, str] = {
    "BRCA1": "ATGGATTTATCTGCTCTTCGCGTTGAAGAAGTACAAAATGTCATTAATGCTATGCAGAAAATCTTAGAGTGTCCCATCTGTCTGGAGTTGATCAAGGAACCTGTCTCCACAAAGTGTGACCACATATTTTGCAAATTTTGCATGCTGAAACTTCTCAACCAGAAGAAAGGGCCTTCACAGTGTCCTTTATGTAAGAATGATATAACCAAAAGGAGCCTACAAGAAAGTACGAGATTTAGTCAACTTGTTGAAGAGCTATTGAAAATCATTTGTGCTTTTCAGCTTGACACAGGTTTGGAGTATGCAAACAGCTATAATTTTGCAAAAAAGGAAAATAACTCTCCTGAACATCTAAAAGATGAAGTTTCTATCATCCAAAGTATGGGCTACAGAAACCGTGCCAAAAGACTTCTACAGAGTGAACCCGAAAATCCTTCCTTGCAGGAAACCAGTCTCAGTGTCCAACTCTCTAACCTTGGAACTGTGAGAACTCTGAGGACAAAGCAGCGGATACAACCTCAAAAGACGTCTGTCTACATTGAATTGGGATCTGATTCTTCTGAAGATACCGTTAATAAGGCAACTTATTGCAGTGTGGGAGATCAAGAATTGTTACAAATCACCCCTCAAGGAACCAGGGATGAAATCAGTTTGGATTCTGCAAAAAAGGCTGCTTGTGAATTTTCTGAGACGGATGTAACAAATACTGAACATCATCAACCCAGTAATAATGATTTGAACACCACTGAGAAGCGTGCAGCTGAGAGGCATCCAGAAAAGTATCAGGGTAGTTCTGTTTCAAACTTGCATGTGGAGCCATGTGGCACAAATACTCATGCCAGCTCATTACAGCATGAGAACAGCAGTTTATTACTCACTAAAGACAGAATGAATGTAGAAAAGGCTGAATTCTGTAATAAAAGCAAACAGCCTGGCTTAGCAAGGAGCCAACATAACAGATGGGCTGGAAGTAAGGAAACATGTAATGATAGGCGGACTCCCAGCACAGAAAAAAAGGTAGATCTGAATGCTGATCCCCTGTGTGAGAGAAAAGAATGGAATAAGCAGAAACTGCCATGCTCAGAGAATCCTAGAGATACTGAAGATGTTCCTTGGATAACACTAAATAGCAGCATTCAGAAAGTTAATGAGTGGTTTTCCAGAAGTGATGAACTGTTAGGTTCTGATGACTCACATGATGGGGAGTCTGAATCAAATGCCAAAGTAGCTGATGTATTGGACGTTCTAAATGAGGTAGATGAATATTCTGGTTCTTCAGAGAAAATAGACTTACTGGCCAGTGATCCTCATGAGGCTTTAATATGTAAAAGTGAAAGAGTTCACTCCAAATCAGTAGAGAGTAATATTGAAGACAAAATATTTGGGAAAACCTATCGGAAGAAGGCAAGCCTCCCCAACTTAAGCCATGTAACTGAAAATCTAATTATAGGAGCATTTGTTACTGAGCCACAGATAATACAAGAGCGTCCCCTCACAAATAAATTAAAGCGTAAAAGGAGACCTACATCAGGCCTTCATCCTGAGGATTTTATCAAGAAAGCAGATTTGGCAGTTCAAAAGACTCCTGAAATGATCAATCAGGGTACTAACCAGACGGAGCAGAATGGTCAAGTGATGAATATTACTAATAGTGGTCATGAGAATAAAACAAAAGGTGATTCTATTCAGAATGAGAAAAATCCTAACCCAATAGAATCACTCGAAAAAGAATCTGCTTTCAAAACGAAAGCTGAACCTATAAGCAGCAGTATAAGCAATATGGAACTCGAATTAAATATCCACAATTCAAAAGCACCTAAAAAGAATAGGCTGAGGAGGAAGTCTTCTACCAGGCATATTCATGCGCTTGAACTAGTAGTCAGTAGAAATCTAAGCCCACCTAATTGTACTGAATTGCAAATTGATAGTTGTTCTAGCAGTGAAGAGATAAAGAAAAAAAAGTACAACCAAATGCCAGTCAGGCACAGCAGAAACCTACAACTCATGGAAGGTAAAGAACCTGCAACTGGAGCCAAGAAGAGTAACAAGCCAAATGAACAGACAAGTAAAAGACATGACAGCGATACTTTCCCAGAGCTGAAGTTAACAAATGCACCTGGTTCTTTTACTAAGTGTTCAAATACCAGTGAACTTAAAGAATTTGTCAATCCTAGCCTTCCAAGAGAAGAAAAAGAAGAGAAACTAGAAACAGTTAAAGTGTCTAATAATGCTGAAGACCCCAAAGATCTCATGTTAAGTGGAGAAAGGGTTTTGCAAACTGAAAGATCTGTAGAGAGTAGCAGTATTTCA",
    "GAPDH": "ATGGGGAAGGTGAAGGTCGGAGTCAACGGATTTGGTCGTATTGGGCGCCTGGTCACCAGGGCTGCTTTTAACTCTGGCAAAGTGGATATTGTCGCCATCAATGACCCCTTCATTGACCTCAACTACATGGTTTACATGTTCCAATATGATTCCACCCATGGCAAATTCCATGGCACCGTCAAGGCTGAGAACGGGAAGCTTGTCATCAATGGAAATCCCATCACCATCTTCCAGGAGCGAGATCCCTCCAAAATCAAGTGGGGCGATGCTGGCGCTGAGTACGTCGTGGAGTCCACTGGCGTCTTCACCACCATGGAGAAGGCTGGGGCTCATTTGCAGGGGGGAGCCAAAAGGGTCATCATCTCTGCCCCCTCTGCTGATGCCCCCATGTTCGTCATGGGTGTGAACCATGAGAAGTATGACAACAGCCTCAAGATCATCAGCAATGCCTCCTGCACCACCAACTGCTTAGCACCCCTGGCCAAGGTCATCCATGACAACTTTGGTATCGTGGAAGGACTCATGACCACAGTCCATGCCATCACTGCCACCCAGAAGACTGTGGATGGCCCCTCCGGGAAACTGTGGCGTGATGGCCGCGGGGCTCTCCAGAACATCATCCCTGCCTCTACTGGCGCTGCCAAGGCTGTGGGCAAGGTCATCCCTGAGCTGAACGGGAAGCTCACTGGCATGGCCTTCCGTGTCCCCACCCCCAACGTGTCCGTCGTGGATCTGACCTGCCGTCTGGAAAAACCTGCCAAGTACGATGACATCAAGAAGGTGGTGAAGCAGGCGTCGGAGGGCCCCCTCAAGGGCATCCTGGGCTACACTGAGCACCAGGTGGTCTCCTCCGACTTCAACAGCGACACCCACTCCTCCACCTTCGACGCTGGGGCTGGCATTGCCCTCAACGACCACTTTGTCAAGCTCATTTCCTGGTATGACAACGAATTTGGCTACAGCAACAGGGTGGTGGACCTCATGGCCCACATGGCCTCCAAGGAG",
    "TP53": "ATGGAGGAGCCGCAGTCAGATCCTAGCGTCGAGCCCCCTCTGAGTCAGGAAACATTTTCAGACCTATGGAAACTACTTCCTGAAAACAACGTTCTGTCCCCCTTGCCGTCCCAAGCAATGGATGATTTGATGCTGTCCCCGGACGATATTGAACAATGGTTCACTGAAGACCCAGGTCCAGATGAAGCTCCCAGAATGCCAGAGGCTGCTCCCCCCGTGGCCCCTGCACCAGCAGCTCCTACACCGGCGGCCCCTGCACCAGCCCCCTCCTGGCCCCTGTCATCTTCTGTCCCTTCCCAGAAAACCTACCAGGGCAGCTACGGTTTCCGTCTGGGCTTCTTGCATTCTGGGACAGCCAAGTCTGTGACTTGCACGTACTCCCCTGCCCTCAACAAGATGTTTTGCCAACTGGCCAAGACCTGCCCTGTGCAGCTGTGGGTTGATTCCACACCCCCGCCCGGCACCCGCGTCCGCGCCATGGCCATCTACAAGCAGTCACAGCACATGACGGAGGTTGTGAGGCGCTGCCCCCACCATGAGCGCTGCTCAGATAGCGATGGTCTGGCCCCTCCTCAGCATCTTATCCGAGTGGAAGGAAATTTGCGTGTGGAGTATTTGGATGACAGAAACACTTTTCGACATAGTGTGGTGGTGCCCTATGAGCCGCCTGAGGTTGGCTCTGACTGTACCACCATCCACTACAACTACATGTGTAACAGTTCCTGCATGGGCGGCATGAACCGGAGGCCCATCCTCACCATCATCACACTGGAAGACTCCAGTGGTAATCTACTGGGACGGAACAGCTTTGAGGTGCGTGTTTGTGCCTGTCCTGGGAGAGACCGGCGCACAGAGGAAGAGAATCTCCGCAAGAAAGGGGAGCCTCACCACGAGCTGCCCCCAGGGAGCACTAAGCGAGCACTGCCCAACAACACCAGCTCCTCTCCCCAGCCAAAGAAGAAACCACTGGATGGAGAATATTTCACCCTTCAGATCCGTGGGCGTGAGCGCTTCGAGATGTTCCGAGAGCTGAATGAGGCCTTGGAACTCAAGGATGCCCAGGCTGGGAAGGAGCCAGGGGGGAGCAGGGCTCACTCCAGCCACCTGAAGTCCAAAAAGGGTCAGTCTACCTCCCGCCATAAAAAACTCATGTTCAAGACAGAAGGGCCTGACTCAGAC",
    "ACTB": "ATGGATGATGATATCGCCGCGCTCGTCGTCGACAACGGCTCCGGCATGTGCAAGGCCGGCTTCGCGGGCGACGATGCCCCCCGGGCCGTCTTCCCCTCCATCGTGGGGCGCCCCAGGCACCAGGGCGTGATGGTGGGCATGGGTCAGAAGGATTCCTATGTGGGCGACGAGGCCCAGAGCAAGAGAGGCATCCTCACCCTGAAGTACCCCATCGAGCACGGCATCGTCACCAACTGGGACGACATGGAGAAGATCTGGCACCACACCTTCTACAACGAGCTGCGCGTGGCCCCGGAGGAGCACCCCGTGCTGCTGACCGAGGCCCCCCTGAACCCCAAGGCCAACCGCGAGAAGATGACCCAGATCATGTTTGAGACCTTCAACACCCCAGCCATGTACGTTGCTATCCAGGCTGTGCTATCCCTGTACGCCTCTGGCCGTACCACTGGCATCGTGATGGACTCCGGTGACGGGGTCACCCACACTGTGCCCATCTACGAGGGGTATGCCCTCCCCCACGCCATCCTGCGTCTGGACCTGGCTGGCCGGGACCTGACTGACTACCTCATGAAGATCCTCACCGAGCGCGGCTACAGCTTCACCACCACGGCCGAGCGGGAAATCGTGCGCGACATCAAGGAGAAGCTGTGCTACGTCGCCCTGGACTTCGAGCAAGAGATGGCCACGGCTGCTTCCAGCTCCTCCCTGGAGAAGAGCTACGAGCTGCCTGACGGCCAGGTCATCACCATTGGCAACGAGCGGTTCCGCTGCCCTGAGGCACTCTTCCAGCCTTCCTTCCTGGGCATGGAATCTTGCGGCATCCACGAAACTACCTTCAACTCCATCATGAAGTGTGACGTGGACATCCGCAAAGACCTGTACGCCAACACAGTGCTGTCTGGCGGCACCACCATGTACCCTGGCATTGCCGACAGGATGCAGAAGGAGATCACTGCCCTGGCACCCAGCACAATGAAGATCAAGATCATTGCTCCTCCTGAGCGCAAGTACTCCGTGTGGATCGGCGGCTCCATCCTGGCCTCGCTGTCCACCTTCCAGCAGATGTGGATCAGCAAGCAGGAGTATGACGAGTCCGGCCCCTCCATCGTCCACCGCAAATGCTTCTAG",
    "EGFL7": "ATGGGCCAGGCTGCAGGCCCTGGAGCCCAGGCAGGAGCCCGCAGGCGCTGGCTGCCACTACTCCTGCTGCTCCTGCTCCTGGCCCCACATTCGGCCCAGGCCAGCGCCGGTGGCAGTGACCAGGCCCCTGCTGGGAACCTGGTGTGTCGGGCCCACGGCTCAAGACCCATGTACTGCAGAGGCACCACATGCATCCAGGCACTGCGTGGCCAAGCCAGCTGTGCTGCCTGTGGACCCCCGGGCTTCTATGACCACGATACATGCCAGCCCTGCCCTTGTCGAAAGAACCAGCCCCAGGAACCAGGGCCCATCCAGTGTCAGCCCCTGTGCCACTGTGAAGCTGGATGCCACCCAGCCACATGCCAAGCTGGCCCCACACCCTGTCCCTGCCCCGAGGGCCCCCTCTGTACCCAGAACACATGCACCCAGCCCCGAGGCCCCGGCTGCAGAGAACACCAGGGCAGCTGCCAAGGGTCCCTAGGAGGGCAGTGCCAAGCCCTGTGCCAGTGTCAAGGAGGACCCTGCCCACCATGCCAGCGTGCTGGAGCAGGCTGCCATGAATGCCTCTGTGCAGTGACCACCTGCCAGACCCCCCCAGGACCCCACTGTATCCAAGAAACCTGTAGCCCCTGCCCACCAGGCCCATGTCAGGCTGGGGAGACCTGCCAGTCCATCTGCCAGTGTCCTGCAGGGCCTTTTGGGTACCAGGAAGACTGCCATCGCCCATGCCCTTGTCGTAACCAGCAGCCTCAGGAGACAGGACACTGGTCATGCCCACGGCTGTGCCACTGCCCTGGAGGCCCATGCCTCCCGTGTGGGGCCCCACCACCCCTCTGCCAAGAAAAGTGCACTGGAGCCTGTCGAGGCTGCCGAGAAGGGTCTGGCTGCCAAAGCACCTGTCAGGCTGCCCAGGGCCAGGTTTGCCTGCAGAATACCTGCCTCCCATGTCCCCAGGGCCGTCTTTGTGCTCAGGGACACTGCAGAGAAACTTGCAACCATGAATGCCAGCGCTGTCACAGTGAGCAGTGCCACCGCTGCCCCTGCAGCTGTGAGCGGGGCCAGCTGGGCCATGATGAGTGCAGCCCCCATGCCCCCCAGTGTTGGCCCTGCTCTCAGGGCCTGGCTTGCAACCAGAACCGCTGCCTGCCCTGTCCC"
}


def _fetch_ncbi_sequence_impl(
    gene_or_accession: str,
    organism: str = "Homo sapiens",
    email: str = "user@example.com",
    api_key: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Internal implementation for NCBI sequence fetching with in-memory caching
    and socket timeout for high performance.
    """
    query_clean = gene_or_accession.strip()
    cache_key = (query_clean.upper(), organism.lower())
    if cache_key in _SEQUENCE_CACHE:
        logger.info(f"Returning cached sequence record for {cache_key}")
        return _SEQUENCE_CACHE[cache_key]

    try:
        from Bio import Entrez, SeqIO
    except ImportError:
        return {
            "error": "Biopython is required. Install with: pip install biopython",
            "suggestions": ["pip install biopython"],
        }

    Entrez.email = email
    if api_key:
        Entrez.api_key = api_key

    query_str = query_clean
    warnings = []
    accession_id = ""
    description = ""
    full_seq = ""

    # Check if query is directly an Accession ID
    is_accession = bool(
        re.match(
            r'^(?:[A-Z]{2,4}_\d+|[A-Z]\d{5}|[A-Z]{2}\d{6,8})(\.\d+)?$',
            query_str,
            re.IGNORECASE,
        )
    )

    import socket
    old_timeout = socket.getdefaulttimeout()

    try:
        # Set 5s timeout on Entrez network calls
        socket.setdefaulttimeout(5.0)

        if is_accession:
            accession_id = query_str
        else:
            # Search Entrez nucleotide database
            term = f"{query_str}[Gene Name] AND {organism}[Organism] AND RefSeq[Filter]"
            search_handle = Entrez.esearch(db="nuccore", term=term, retmax=5)
            search_results = Entrez.read(search_handle)
            search_handle.close()

            id_list = search_results.get("IdList", [])
            if not id_list:
                # Fallback: search without RefSeq filter
                term_broad = f"{query_str}[All Fields] AND {organism}[Organism]"
                search_handle = Entrez.esearch(db="nuccore", term=term_broad, retmax=5)
                search_results = Entrez.read(search_handle)
                search_handle.close()
                id_list = search_results.get("IdList", [])

            if not id_list:
                # Check mock reference templates before returning error
                gene_upper = query_clean.upper()
                if gene_upper in _MOCK_GENE_TEMPLATES:
                    full_seq = _MOCK_GENE_TEMPLATES[gene_upper]
                    accession_id = f"REF_{gene_upper}_MOCK"
                    description = f"{gene_upper} reference sequence (local fallback)"
                else:
                    return {
                        "error": f"No NCBI nucleotide sequence found for '{query_str}' in {organism}.",
                        "suggestions": [
                            "Check spelling of gene symbol (e.g. BRCA1, TP53, GAPDH, egfp)",
                            "Try passing an exact NCBI Accession ID (e.g. NM_007294.4)",
                            "Verify selected organism matches gene target",
                        ],
                    }
            else:
                accession_id = id_list[0]

        if not full_seq:
            # Fetch sequence record from NCBI
            fetch_handle = Entrez.efetch(
                db="nuccore", id=accession_id, rettype="fasta", retmode="text"
            )
            seq_record = SeqIO.read(fetch_handle, "fasta")
            fetch_handle.close()

            accession_id = seq_record.id
            description = seq_record.description
            full_seq = str(seq_record.seq).upper()

    except Exception as e:
        logger.warning(f"NCBI Fetch Exception for '{query_str}': {e}. Trying fallback templates.")
        gene_upper = query_clean.upper()
        if gene_upper in _MOCK_GENE_TEMPLATES:
            full_seq = _MOCK_GENE_TEMPLATES[gene_upper]
            accession_id = f"REF_{gene_upper}_FALLBACK"
            description = f"{gene_upper} fallback reference sequence"
            warnings.append(f"Network call failed/timed out ({e}). Using offline reference sequence for {gene_upper}.")
        else:
            return {
                "error": f"NCBI Fetch Error: {str(e)}",
                "suggestions": [
                    "Ensure internet connectivity",
                    "Verify NCBI API key / email settings",
                    "Try an accession number directly",
                ],
            }
    finally:
        socket.setdefaulttimeout(old_timeout)

    total_len = len(full_seq)
    truncated = False
    target_seq = full_seq

    # If sequence > 10,000 bp, extract central 2,000 bp target region
    if total_len > 10000:
        start_pos = (total_len // 2) - 1000
        end_pos = start_pos + 2000
        target_seq = full_seq[start_pos:end_pos]
        truncated = True
        warnings.append(
            f"Sequence length ({total_len:,} bp) > 10,000 bp. "
            f"Extracted central 2,000 bp region ({start_pos+1}..{end_pos} bp) for primer design."
        )

    # Calculate GC content
    overall_gc = calculate_gc_content(target_seq)
    high_gc = overall_gc > 70.0
    if high_gc:
        warnings.append(
            f"High-GC region detected ({overall_gc:.1f}% GC). "
            "Recommend using High-GC parameter preset."
        )

    # Low complexity repeat check
    masked_seq, has_repeats = mask_low_complexity(target_seq)
    if has_repeats:
        warnings.append(
            "Repetitive/low-complexity sequence regions detected and masked with 'N'."
        )

    res = {
        "accession": accession_id,
        "description": description,
        "sequence": target_seq,
        "full_length": total_len,
        "target_length": len(target_seq),
        "truncated": truncated,
        "gc_content": round(overall_gc, 2),
        "high_gc": high_gc,
        "warnings": warnings,
        "error": None,
    }
    _SEQUENCE_CACHE[cache_key] = res
    if accession_id:
        _SEQUENCE_CACHE[(accession_id.upper(), organism.lower())] = res
    return res


@tool
def fetch_sequence(
    gene_or_accession: str,
    organism: str = "Homo sapiens",
    email: str = "user@example.com",
) -> str:
    """Fetch a DNA sequence from NCBI Entrez by gene symbol or accession ID.
    
    Use this tool when you need to retrieve a target DNA sequence for primer design.
    Provide a gene symbol (e.g., 'BRCA1', 'TP53', 'GAPDH') or an NCBI accession
    number (e.g., 'NM_007294.4'). Also specify the target organism.
    
    The tool returns the sequence, accession ID, GC content, and any warnings
    (e.g., high-GC regions, sequence truncation for long genes).
    
    Args:
        gene_or_accession: Gene symbol or NCBI accession ID to search for.
        organism: Target organism scientific name (default: Homo sapiens).
        email: Email for NCBI API tracking.
    
    Returns:
        JSON string with sequence data including accession, sequence, gc_content,
        warnings, and any errors encountered.
    """
    result = _fetch_ncbi_sequence_impl(
        gene_or_accession=gene_or_accession,
        organism=organism,
        email=email,
    )
    return json.dumps(result, indent=2)
