"""
PrimerAgent Database Models — Schema Definitions (v3.0)

Defines the database schema for storing primer designs, reasoning traces,
In-Silico PCR results, genome assembly metadata, and experiment conditions.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List, Dict, Any


@dataclass
class PrimerDesignRecord:
    """
    Complete record of a primer design session in PrimerAgent v3.0.
    """
    # Identity
    id: Optional[int] = None
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())

    # Target information
    gene_symbol: str = ""
    organism: str = ""
    genome_assembly: str = "GRCh38"
    accession_id: str = ""
    transcript_id: str = ""
    application: str = ""

    # Primer sequences
    fwd_sequence: str = ""
    rev_sequence: str = ""
    fwd_tm: float = 0.0
    rev_tm: float = 0.0
    fwd_gc: float = 0.0
    rev_gc: float = 0.0
    tm_diff: float = 0.0
    amplicon_length: int = 0

    # In-Silico PCR Validation (v3.0)
    in_silico_pcr_status: str = "PASS"
    in_silico_pcr_engine: str = "Local Engine"
    amplicon_count: int = 1
    exon_junction_status: bool = False
    genomic_dna_risk: str = "reduced"

    # Validation scores
    quality_score: float = 0.0
    specificity_score: float = 0.0
    hairpin_mfe_fwd: float = 0.0
    hairpin_mfe_rev: float = 0.0
    self_dimer_mfe_fwd: float = 0.0
    self_dimer_mfe_rev: float = 0.0
    hetero_dimer_mfe: float = 0.0

    # BLAST summary
    blast_fwd_off_targets: int = 0
    blast_rev_off_targets: int = 0

    # Validation status: 'computational', 'wet_lab_validated', 'published'
    validation_status: str = "computational"

    # ReAct reasoning
    reasoning_trace: str = ""   # JSON of full Thought/Action/Observation
    confidence_score: float = 0.0

    # Experiment metadata
    experiment_notes: str = ""
    pcr_conditions: str = ""    # JSON of recommended conditions

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "id": self.id,
            "created_at": self.created_at,
            "gene_symbol": self.gene_symbol,
            "organism": self.organism,
            "genome_assembly": self.genome_assembly,
            "accession_id": self.accession_id,
            "transcript_id": self.transcript_id,
            "application": self.application,
            "fwd_sequence": self.fwd_sequence,
            "rev_sequence": self.rev_sequence,
            "fwd_tm": self.fwd_tm,
            "rev_tm": self.rev_tm,
            "fwd_gc": self.fwd_gc,
            "rev_gc": self.rev_gc,
            "tm_diff": self.tm_diff,
            "amplicon_length": self.amplicon_length,
            "in_silico_pcr_status": self.in_silico_pcr_status,
            "in_silico_pcr_engine": self.in_silico_pcr_engine,
            "amplicon_count": self.amplicon_count,
            "exon_junction_status": self.exon_junction_status,
            "genomic_dna_risk": self.genomic_dna_risk,
            "quality_score": self.quality_score,
            "specificity_score": self.specificity_score,
            "hairpin_mfe_fwd": self.hairpin_mfe_fwd,
            "hairpin_mfe_rev": self.hairpin_mfe_rev,
            "self_dimer_mfe_fwd": self.self_dimer_mfe_fwd,
            "self_dimer_mfe_rev": self.self_dimer_mfe_rev,
            "hetero_dimer_mfe": self.hetero_dimer_mfe,
            "blast_fwd_off_targets": self.blast_fwd_off_targets,
            "blast_rev_off_targets": self.blast_rev_off_targets,
            "validation_status": self.validation_status,
            "reasoning_trace": self.reasoning_trace,
            "confidence_score": self.confidence_score,
            "experiment_notes": self.experiment_notes,
            "pcr_conditions": self.pcr_conditions,
        }
