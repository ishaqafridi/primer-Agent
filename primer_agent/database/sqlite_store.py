"""
PrimerAgent SQLite Store — File-Based Primer Design Database (v3.0)

Provides a zero-configuration SQLite database for storing and retrieving
primer designs, enabling search by gene/organism and export to CSV/JSON.
"""

import json
import sqlite3
import logging
from typing import Dict, Any, List, Optional
from pathlib import Path

from primer_agent.database.models import PrimerDesignRecord

logger = logging.getLogger(__name__)

CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS primer_designs (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at          TEXT DEFAULT (datetime('now')),
    gene_symbol         TEXT NOT NULL,
    organism            TEXT NOT NULL,
    genome_assembly     TEXT DEFAULT 'GRCh38',
    accession_id        TEXT,
    transcript_id       TEXT,
    application         TEXT NOT NULL,
    fwd_sequence        TEXT NOT NULL,
    rev_sequence        TEXT NOT NULL,
    fwd_tm              REAL,
    rev_tm              REAL,
    fwd_gc              REAL,
    rev_gc              REAL,
    tm_diff             REAL,
    amplicon_length     INTEGER,
    in_silico_pcr_status TEXT DEFAULT 'PASS',
    in_silico_pcr_engine TEXT DEFAULT 'Local Engine',
    amplicon_count      INTEGER DEFAULT 1,
    exon_junction_status INTEGER DEFAULT 0,
    genomic_dna_risk    TEXT DEFAULT 'reduced',
    quality_score       REAL,
    specificity_score   REAL,
    hairpin_mfe_fwd     REAL,
    hairpin_mfe_rev     REAL,
    self_dimer_mfe_fwd  REAL,
    self_dimer_mfe_rev  REAL,
    hetero_dimer_mfe    REAL,
    blast_fwd_off_targets INTEGER,
    blast_rev_off_targets INTEGER,
    validation_status   TEXT DEFAULT 'computational',
    reasoning_trace     TEXT,
    confidence_score    REAL,
    experiment_notes    TEXT,
    pcr_conditions      TEXT
);

CREATE INDEX IF NOT EXISTS idx_gene ON primer_designs(gene_symbol);
CREATE INDEX IF NOT EXISTS idx_organism ON primer_designs(organism);
CREATE INDEX IF NOT EXISTS idx_score ON primer_designs(quality_score DESC);
CREATE INDEX IF NOT EXISTS idx_status ON primer_designs(validation_status);
"""


class PrimerDatabase:
    """
    SQLite-based primer design database.
    """

    def __init__(self, db_path: str = "primer_designs.db"):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        """Create the database schema if it doesn't exist."""
        conn = sqlite3.connect(self.db_path)
        try:
            conn.executescript(CREATE_TABLE_SQL)
            conn.commit()
            self._apply_migrations(conn)
        finally:
            conn.close()
        logger.info(f"PrimerDatabase initialized: {self.db_path}")

    def _apply_migrations(self, conn: sqlite3.Connection):
        """Migrate existing DB schemas to include v3.0 columns if needed."""
        cursor = conn.cursor()
        cursor.execute("PRAGMA table_info(primer_designs)")
        columns = [row[1] for row in cursor.fetchall()]

        new_cols = [
            ("genome_assembly", "TEXT DEFAULT 'GRCh38'"),
            ("in_silico_pcr_status", "TEXT DEFAULT 'PASS'"),
            ("in_silico_pcr_engine", "TEXT DEFAULT 'Local Engine'"),
            ("amplicon_count", "INTEGER DEFAULT 1"),
            ("exon_junction_status", "INTEGER DEFAULT 0"),
            ("genomic_dna_risk", "TEXT DEFAULT 'reduced'"),
        ]

        for col_name, col_def in new_cols:
            if col_name not in columns:
                try:
                    cursor.execute(f"ALTER TABLE primer_designs ADD COLUMN {col_name} {col_def}")
                    logger.info(f"Added migration column: {col_name}")
                except Exception as e:
                    logger.debug(f"Column migration notice for {col_name}: {e}")
        conn.commit()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def save_design(self, record: PrimerDesignRecord) -> int:
        conn = self._get_connection()
        try:
            cursor = conn.execute("""
                INSERT INTO primer_designs (
                    created_at, gene_symbol, organism, genome_assembly, accession_id, transcript_id,
                    application, fwd_sequence, rev_sequence, fwd_tm, rev_tm,
                    fwd_gc, rev_gc, tm_diff, amplicon_length, in_silico_pcr_status,
                    in_silico_pcr_engine, amplicon_count, exon_junction_status, genomic_dna_risk,
                    quality_score, specificity_score, hairpin_mfe_fwd, hairpin_mfe_rev,
                    self_dimer_mfe_fwd, self_dimer_mfe_rev, hetero_dimer_mfe,
                    blast_fwd_off_targets, blast_rev_off_targets, validation_status,
                    reasoning_trace, confidence_score, experiment_notes, pcr_conditions
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                record.created_at, record.gene_symbol, record.organism, record.genome_assembly,
                record.accession_id, record.transcript_id, record.application,
                record.fwd_sequence, record.rev_sequence, record.fwd_tm, record.rev_tm,
                record.fwd_gc, record.rev_gc, record.tm_diff, record.amplicon_length,
                record.in_silico_pcr_status, record.in_silico_pcr_engine, record.amplicon_count,
                1 if record.exon_junction_status else 0, record.genomic_dna_risk,
                record.quality_score, record.specificity_score,
                record.hairpin_mfe_fwd, record.hairpin_mfe_rev,
                record.self_dimer_mfe_fwd, record.self_dimer_mfe_rev,
                record.hetero_dimer_mfe,
                record.blast_fwd_off_targets, record.blast_rev_off_targets,
                record.validation_status, record.reasoning_trace,
                record.confidence_score, record.experiment_notes, record.pcr_conditions,
            ))
            conn.commit()
            record_id = cursor.lastrowid
            logger.info(f"Saved primer design #{record_id}: {record.gene_symbol}")
            return record_id
        finally:
            conn.close()

    def search(
        self,
        gene_symbol: Optional[str] = None,
        organism: Optional[str] = None,
        application: Optional[str] = None,
        min_score: Optional[float] = None,
        validation_status: Optional[str] = None,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        conn = self._get_connection()
        try:
            conditions = []
            params = []

            if gene_symbol:
                conditions.append("UPPER(gene_symbol) = UPPER(?)")
                params.append(gene_symbol)
            if organism:
                conditions.append("UPPER(organism) LIKE UPPER(?)")
                params.append(f"%{organism}%")
            if application:
                conditions.append("application = ?")
                params.append(application)
            if min_score is not None:
                conditions.append("quality_score >= ?")
                params.append(min_score)
            if validation_status:
                conditions.append("validation_status = ?")
                params.append(validation_status)

            where_clause = " AND ".join(conditions) if conditions else "1=1"
            query = f"""
                SELECT * FROM primer_designs
                WHERE {where_clause}
                ORDER BY quality_score DESC
                LIMIT ?
            """
            params.append(limit)

            cursor = conn.execute(query, params)
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
        finally:
            conn.close()

    def get_by_id(self, record_id: int) -> Optional[Dict[str, Any]]:
        conn = self._get_connection()
        try:
            cursor = conn.execute(
                "SELECT * FROM primer_designs WHERE id = ?", (record_id,)
            )
            row = cursor.fetchone()
            return dict(row) if row else None
        finally:
            conn.close()

    def delete_design(self, record_id: int) -> bool:
        """Delete a primer design record by ID."""
        conn = self._get_connection()
        try:
            cursor = conn.execute("DELETE FROM primer_designs WHERE id = ?", (record_id,))
            conn.commit()
            return cursor.rowcount > 0
        finally:
            conn.close()

    def get_stats(self) -> Dict[str, Any]:
        conn = self._get_connection()
        try:
            total = conn.execute("SELECT COUNT(*) FROM primer_designs").fetchone()[0]
            passed = conn.execute(
                "SELECT COUNT(*) FROM primer_designs WHERE quality_score >= 60"
            ).fetchone()[0]
            organisms = conn.execute(
                "SELECT DISTINCT organism FROM primer_designs WHERE organism != ''"
            ).fetchall()
            genes = conn.execute(
                "SELECT DISTINCT gene_symbol FROM primer_designs WHERE gene_symbol != ''"
            ).fetchall()

            return {
                "total_designs": total,
                "passed_designs": passed,
                "pass_rate": round(passed / total * 100, 1) if total > 0 else 0,
                "unique_organisms": len(organisms),
                "unique_genes": len(genes),
            }
        finally:
            conn.close()

    def export_csv_str(self, **search_kwargs) -> str:
        """Export search results directly as a CSV string for in-browser download."""
        import csv
        import io

        results = self.search(**search_kwargs)
        if not results:
            return ""

        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=results[0].keys())
        writer.writeheader()
        writer.writerows(results)
        return output.getvalue()

    def export_json_str(self, **search_kwargs) -> str:
        """Export search results directly as a formatted JSON string for in-browser download."""
        results = self.search(**search_kwargs)
        return json.dumps(results, indent=2, default=str)

    def export_csv(self, filepath: str, **search_kwargs) -> str:
        results = self.search(**search_kwargs)
        if not results:
            return "No results to export."

        import csv
        with open(filepath, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=results[0].keys())
            writer.writeheader()
            writer.writerows(results)

        return f"Exported {len(results)} records to {filepath}"

    def save_from_agent_result(
        self, agent_result: Dict[str, Any],
    ) -> List[int]:
        saved_ids = []
        state = agent_result.get("state", {})
        confidence = agent_result.get("confidence", {})
        trace_json = json.dumps(agent_result.get("reasoning_trace", []), default=str)

        for eval_res in agent_result.get("validated_results", []):
            cand = eval_res.get("candidate", {})
            fwd_struct = eval_res.get("fwd_struct", {})
            rev_struct = eval_res.get("rev_struct", {})
            hetero_struct = eval_res.get("hetero_struct", {})
            fwd_blast = eval_res.get("fwd_blast", {})
            rev_blast = eval_res.get("rev_blast", {})
            pcr_res = eval_res.get("pcr_result", {})
            exon_res = eval_res.get("exon_result", {})

            record = PrimerDesignRecord(
                gene_symbol=state.get("gene_name", ""),
                organism=state.get("organism", ""),
                genome_assembly=state.get("genome_assembly", "GRCh38"),
                accession_id=state.get("accession", ""),
                transcript_id=state.get("transcript_accession", ""),
                application=state.get("application", ""),
                fwd_sequence=cand.get("fwd_seq", ""),
                rev_sequence=cand.get("rev_seq", ""),
                fwd_tm=cand.get("fwd_tm", 0.0),
                rev_tm=cand.get("rev_tm", 0.0),
                fwd_gc=cand.get("fwd_gc", 0.0),
                rev_gc=cand.get("rev_gc", 0.0),
                tm_diff=cand.get("tm_diff", 0.0),
                amplicon_length=cand.get("product_size", 0),
                in_silico_pcr_status=pcr_res.get("status", "PASS") if isinstance(pcr_res, dict) else "PASS",
                in_silico_pcr_engine=pcr_res.get("engine_used", "Local Engine") if isinstance(pcr_res, dict) else "Local Engine",
                amplicon_count=pcr_res.get("amplicon_count", 1) if isinstance(pcr_res, dict) else 1,
                exon_junction_status=bool(exon_res.get("exon_junction", False)) if isinstance(exon_res, dict) else False,
                genomic_dna_risk=exon_res.get("genomic_dna_risk", "reduced") if isinstance(exon_res, dict) else "reduced",
                quality_score=eval_res.get("score", 0.0) if eval_res.get("score") is not None else 0.0,
                hairpin_mfe_fwd=fwd_struct.get("hairpin_mfe", 0.0) if isinstance(fwd_struct, dict) else 0.0,
                hairpin_mfe_rev=rev_struct.get("hairpin_mfe", 0.0) if isinstance(rev_struct, dict) else 0.0,
                self_dimer_mfe_fwd=fwd_struct.get("self_dimer_mfe", 0.0) if isinstance(fwd_struct, dict) else 0.0,
                self_dimer_mfe_rev=rev_struct.get("self_dimer_mfe", 0.0) if isinstance(rev_struct, dict) else 0.0,
                hetero_dimer_mfe=hetero_struct.get("hetero_dimer_mfe", 0.0) if isinstance(hetero_struct, dict) else 0.0,
                blast_fwd_off_targets=fwd_blast.get("off_target_hits", 0) if isinstance(fwd_blast, dict) else 0,
                blast_rev_off_targets=rev_blast.get("off_target_hits", 0) if isinstance(rev_blast, dict) else 0,
                reasoning_trace=trace_json,
                confidence_score=confidence.get("confidence_score", 0.0) if isinstance(confidence, dict) else 0.0,
            )
            record_id = self.save_design(record)
            saved_ids.append(record_id)

        return saved_ids
