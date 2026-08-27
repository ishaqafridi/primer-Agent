"""
PrimerAgent Configuration — Constants, Acceptance Criteria, and Parameter Presets

This module centralizes all configurable parameters used across the PrimerAgent
system, including thermodynamic thresholds, Primer-BLAST presets for different
PCR applications, parameter adjustment bounds, and agent behavior settings.

References:
    - Primer-BLAST parameters: Ye et al., BMC Bioinformatics, 2012
    - PCR primer design guidelines: Dieffenbach et al., PCR Methods Appl., 1993
    - qPCR primer criteria: Bustin et al., Clinical Chemistry, 2009
"""


from typing import Dict, Any

# ==============================================================================
# ACCEPTANCE CRITERIA — Thresholds for primer quality validation
# ==============================================================================

ACCEPTANCE_CRITERIA: Dict[str, Any] = {
    # Primer length constraints (nucleotides)
    "length_min": 18,
    "length_max": 25,

    # Melting temperature range (°C) — SantaLucia nearest-neighbor method
    "tm_min": 57.0,
    "tm_max": 63.0,
    "tm_diff_max": 2.0,       # Maximum ΔTm between forward and reverse primers

    # GC content range (%)
    "gc_min": 40.0,
    "gc_max": 60.0,
    "gc_clamp_min": 1,
    "gc_clamp_max": 3,

    # Default amplicon product size range (bp)
    "product_size_default": (100, 300),

    # BLAST specificity thresholds
    "blast_off_targets_max": 1,    # Maximum tolerated off-target hits (≥80% identity)

    # Secondary structure thresholds (kcal/mol)
    # Calibrated for Nearest-Neighbor sliding-window thermodynamic model
    # More negative = more stable (worse for primers)
    "hairpin_mfe_min": -4.0,        # Hairpin: must be > -4.0 kcal/mol
    "self_dimer_mfe_min": -12.0,    # Self-dimer: must be > -12.0 kcal/mol
    "hetero_dimer_mfe_min": -15.0,  # Hetero-dimer: must be > -15.0 kcal/mol

    # Agent behavior
    "min_pass_score": 60.0,        # Minimum score (out of 100) to pass validation (60-100 range)
    "max_iterations": 5,           # Maximum ReAct redesign iterations
    "max_reasoning_steps": 15,     # Maximum ReAct reasoning steps per run
}


# ==============================================================================
# PARAMETER ADJUSTMENT BOUNDS — Enforce biological sanity during iteration
# ==============================================================================

PARAMETER_BOUNDS: Dict[str, float] = {
    "min_tm_lower_limit": 53.0,
    "max_tm_upper_limit": 67.0,
    "min_gc_lower_limit": 30.0,
    "max_gc_upper_limit": 70.0,
    "self_any_th_min": 25.0,
    "self_end_th_min": 15.0,
    "hairpin_th_min": 20.0,
}


# ==============================================================================
# PRIMER3 PARAMETER PRESETS — Application-specific defaults
# ==============================================================================

DEFAULT_PRESETS: Dict[str, Dict[str, Any]] = {
    "Standard PCR": {
        "PRIMER_OPT_SIZE": 20,
        "PRIMER_MIN_SIZE": 18,
        "PRIMER_MAX_SIZE": 25,
        "PRIMER_OPT_TM": 60.0,
        "PRIMER_MIN_TM": 57.0,
        "PRIMER_MAX_TM": 63.0,
        "PRIMER_MIN_GC": 40.0,
        "PRIMER_MAX_GC": 60.0,
        "PRIMER_MAX_POLY_X": 4,
        "PRIMER_SALT_MONOVALENT": 50.0,
        "PRIMER_DNA_CONC": 50.0,
        "PRIMER_MAX_SELF_ANY_TH": 45.0,
        "PRIMER_MAX_SELF_END_TH": 35.0,
        "PRIMER_MAX_HAIRPIN_TH": 40.0,
    },
    "qPCR": {
        "PRIMER_OPT_SIZE": 20,
        "PRIMER_MIN_SIZE": 18,
        "PRIMER_MAX_SIZE": 24,
        "PRIMER_OPT_TM": 60.0,
        "PRIMER_MIN_TM": 58.0,
        "PRIMER_MAX_TM": 62.0,
        "PRIMER_MIN_GC": 45.0,
        "PRIMER_MAX_GC": 60.0,
        "PRIMER_MAX_POLY_X": 3,
        "PRIMER_SALT_MONOVALENT": 50.0,
        "PRIMER_DNA_CONC": 50.0,
        "PRIMER_MAX_SELF_ANY_TH": 40.0,
        "PRIMER_MAX_SELF_END_TH": 30.0,
        "PRIMER_MAX_HAIRPIN_TH": 35.0,
    },
    "Sanger Sequencing": {
        "PRIMER_OPT_SIZE": 21,
        "PRIMER_MIN_SIZE": 19,
        "PRIMER_MAX_SIZE": 25,
        "PRIMER_OPT_TM": 58.0,
        "PRIMER_MIN_TM": 55.0,
        "PRIMER_MAX_TM": 65.0,
        "PRIMER_MIN_GC": 40.0,
        "PRIMER_MAX_GC": 60.0,
        "PRIMER_MAX_POLY_X": 4,
        "PRIMER_SALT_MONOVALENT": 50.0,
        "PRIMER_DNA_CONC": 50.0,
        "PRIMER_MAX_SELF_ANY_TH": 45.0,
        "PRIMER_MAX_SELF_END_TH": 35.0,
        "PRIMER_MAX_HAIRPIN_TH": 40.0,
    },
    "High-GC Preset": {
        "PRIMER_OPT_SIZE": 20,
        "PRIMER_MIN_SIZE": 18,
        "PRIMER_MAX_SIZE": 24,
        "PRIMER_OPT_TM": 62.0,
        "PRIMER_MIN_TM": 59.0,
        "PRIMER_MAX_TM": 65.0,
        "PRIMER_MIN_GC": 50.0,
        "PRIMER_MAX_GC": 70.0,
        "PRIMER_MAX_POLY_X": 3,
        "PRIMER_SALT_MONOVALENT": 50.0,
        "PRIMER_DNA_CONC": 50.0,
        "PRIMER_MAX_SELF_ANY_TH": 50.0,
        "PRIMER_MAX_SELF_END_TH": 40.0,
        "PRIMER_MAX_HAIRPIN_TH": 45.0,
    },
}


# ==============================================================================
# SCORING WEIGHTS — Primer quality evaluation breakdown (total = 100)
# ==============================================================================

SCORING_WEIGHTS: Dict[str, int] = {
    "in_silico_pcr": 25,       # Gate 2: In-Silico PCR single amplicon validation
    "blast_specificity": 20,   # BLAST off-target hits ≤ 1
    "tm_range": 20,            # Both primers within Tm range & ΔTm ≤ 2°C
    "gc_range": 15,            # Both primers within GC% range & 3' clamp
    "hairpin_stability": 10,   # Hairpin & self-dimer stability
    "dimer_stability": 5,      # Hetero-dimer stability
    "exon_validation": 5,      # Exon-exon junction spanning & gDNA risk reduction
}


# ==============================================================================
# GEMINI CONFIGURATION — Model and API settings
# ==============================================================================

GEMINI_CONFIG: Dict[str, Any] = {
    "default_model": "gemini-1.5-flash",
    "fallback_models": ["gemini-2.0-flash", "gemini-1.5-pro", "gemini-2.5-flash"],
    "temperature": 0.2,          # Low temperature for deterministic biological reasoning
    "max_output_tokens": 4096,
    "max_retries": 3,
    "retry_base_delay": 1.0,     # Seconds, exponential backoff
    "rate_limit_rpm": 15,        # Requests per minute (free tier)
}


# ==============================================================================
# REACT AGENT SYSTEM PROMPT — Instructs Gemini on biological reasoning (v3.0)
# ==============================================================================

REACT_SYSTEM_PROMPT = """You are PrimerAgent v3.0, an expert AI bioinformatician specializing in PCR primer design and In-Silico PCR validation.
You operate as a ReAct (Reasoning + Acting) agent, solving primer design tasks through
iterative cycles of Thought → Action → Observation.

Your tool suite includes:
1. RESOLVE_TARGET — Resolve gene symbol, genome assembly (GRCh38/GRCm39), RefSeq accession, and exon structure
2. FETCH_SEQUENCE — Retrieve DNA sequence from NCBI database
3. DESIGN_PRIMERS — Generate candidate primer pairs using Primer-BLAST engine
4. IN_SILICO_PCR — Perform In-Silico PCR validation (UCSC API or Local Reference Engine)
5. VALIDATE_AMPLICON — Audit amplicon size compatibility and product count (qPCR 80-200bp)
6. CHECK_BLAST — Verify primer specificity via BLAST off-target analysis
7. CHECK_STRUCTURE — Analyze secondary structures for hairpins and self-dimers
8. CHECK_HETERODIMER — Check cross-dimer interactions between primer pairs
9. VALIDATE_EXON — Validate exon-exon junction spanning and gDNA contamination risk
10. EVALUATE_PRIMERS — Score primer pairs on 0-100 quality scale with Gate 2 In-Silico PCR enforcement
11. ADJUST_PARAMETERS — Optimize parameters after failed validation (multiple amplicons, Tm, hairpins)

WORKFLOW SEQUENCE:
Target Resolution → Sequence Retrieval → Primer Design → IN-SILICO PCR → Amplicon QC → BLAST Specificity → Structure QC → Dimer QC → Exon QC → Quality Evaluation → PASS/FAIL → Critic Redesign if needed.

CRITICAL PRINCIPLES:
- In-Silico PCR is Gate 2 (HARD VALIDATION GATE). Candidates failing In-Silico PCR (0 amplicons or multiple amplicons) MUST NOT pass validation.
- BLAST checks individual primer binding sites. In-Silico PCR checks paired-primer amplicon generation. Both must be performed.
- Always explain your biological rationale in THOUGHT before choosing an ACTION.

STRICT RESPONSE FORMAT:
THOUGHT: [Your biological reasoning]
ACTION: [Tool name or FINAL_ANSWER]
ACTION_INPUT: [JSON arguments or summary text]
"""


# ==============================================================================
# SUPPORTED ORGANISMS — Common model organisms for the UI
# ==============================================================================

SUPPORTED_ORGANISMS = [
    "Homo sapiens (Human)",
    "Mus musculus (Mouse)",
    "Arabidopsis thaliana (Thale cress)",
    "Saccharomyces cerevisiae (Yeast)",
    "Escherichia coli",
    "Drosophila melanogaster (Fruit fly)",
    "Caenorhabditis elegans (Nematode)",
    "Danio rerio (Zebrafish)",
    "Other / Custom Organism",
]

