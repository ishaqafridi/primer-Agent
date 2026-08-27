"""
PrimerAgent Tool Suite — 9 Bioinformatics Tools for PCR Primer Design (v3.0)

Each tool is decorated with @tool for LangChain/Gemini integration,
enabling the ReAct agent to autonomously select and invoke them.

Tools:
    1. resolve_target — Target & Transcript Resolver (gene, assembly, exons)
    2. fetch_sequence — NCBI Entrez sequence retrieval
    3. design_primers_primer_blast — Primer-BLAST primer pair generation
    4. in_silico_pcr — In-Silico PCR amplicon prediction (UCSC & Local)
    5. validate_amplicon — Amplicon size compatibility & product multiplicity check
    6. blast_check — BLAST off-target specificity analysis
    7. check_structure — Secondary structure & thermodynamic analysis
    8. check_heterodimer_tool — Cross-primer dimer interaction check
    9. validate_exon_transcript — Exon-exon junction spanning & gDNA risk audit
    10. evaluate_primers — Multi-gate quality scoring (0-100)
    11. adjust_params — Intelligent parameter optimization critic
"""

from primer_agent.tools.target_resolver import resolve_target
from primer_agent.tools.sequence_fetcher import fetch_sequence
from primer_agent.tools.primer_blast_designer import design_primers_primer_blast
from primer_agent.tools.in_silico_pcr import in_silico_pcr
from primer_agent.tools.amplicon_validator import validate_amplicon
from primer_agent.tools.blast_checker import blast_check
from primer_agent.tools.structure_checker import check_structure, check_heterodimer_tool
from primer_agent.tools.exon_transcript_validator import validate_exon_transcript
from primer_agent.tools.primer_evaluator import evaluate_primers
from primer_agent.tools.parameter_adjuster import adjust_params

ALL_TOOLS = [
    resolve_target,
    fetch_sequence,
    design_primers_primer_blast,
    in_silico_pcr,
    validate_amplicon,
    blast_check,
    check_structure,
    check_heterodimer_tool,
    validate_exon_transcript,
    evaluate_primers,
    adjust_params,
]
