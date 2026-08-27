-- ============================================================================
-- PrimerAgent Database — PostgreSQL Production Schema
-- ============================================================================
-- This schema is designed for production deployment with PostgreSQL.
-- For development/demo, use the SQLite implementation (sqlite_store.py).
--
-- Features:
--   - Full primer design records with validation metrics
--   - ReAct reasoning trace storage (JSONB for efficient querying)
--   - Experiment metadata and PCR conditions
--   - Indexes for common query patterns
--   - Audit trail with timestamps
-- ============================================================================

-- Drop existing tables if recreating
-- DROP TABLE IF EXISTS primer_designs CASCADE;
-- DROP TABLE IF EXISTS design_sessions CASCADE;

-- ============================================================================
-- Table: design_sessions — Tracks each ReAct agent run
-- ============================================================================
CREATE TABLE IF NOT EXISTS design_sessions (
    id              SERIAL PRIMARY KEY,
    created_at      TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- Target information
    gene_symbol     VARCHAR(50) NOT NULL,
    organism        VARCHAR(100) NOT NULL,
    application     VARCHAR(50) NOT NULL,
    
    -- Agent metadata
    model_used      VARCHAR(50) DEFAULT 'gemini-1.5-flash',
    total_iterations INTEGER DEFAULT 0,
    total_reasoning_steps INTEGER DEFAULT 0,
    execution_time_seconds REAL,
    
    -- Full reasoning trace (JSONB for query efficiency)
    reasoning_trace JSONB,
    
    -- Session status: 'completed', 'failed', 'partial'
    status          VARCHAR(20) DEFAULT 'completed',
    error_message   TEXT,
    
    -- Gemini usage
    input_tokens    INTEGER DEFAULT 0,
    output_tokens   INTEGER DEFAULT 0
);

-- ============================================================================
-- Table: primer_designs — Individual primer pair records
-- ============================================================================
CREATE TABLE IF NOT EXISTS primer_designs (
    id                  SERIAL PRIMARY KEY,
    session_id          INTEGER REFERENCES design_sessions(id) ON DELETE CASCADE,
    created_at          TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- Target information
    gene_symbol         VARCHAR(50) NOT NULL,
    organism            VARCHAR(100) NOT NULL,
    accession_id        VARCHAR(50),
    transcript_id       VARCHAR(50),
    application         VARCHAR(50) NOT NULL,
    
    -- Primer sequences
    fwd_sequence        VARCHAR(100) NOT NULL,
    rev_sequence        VARCHAR(100) NOT NULL,
    fwd_tm              REAL,
    rev_tm              REAL,
    fwd_gc              REAL,
    rev_gc              REAL,
    tm_diff             REAL,
    amplicon_length     INTEGER,
    
    -- Validation scores
    quality_score       REAL,
    specificity_score   REAL,
    
    -- Secondary structure metrics (kcal/mol)
    hairpin_mfe_fwd     REAL,
    hairpin_mfe_rev     REAL,
    self_dimer_mfe_fwd  REAL,
    self_dimer_mfe_rev  REAL,
    hetero_dimer_mfe    REAL,
    
    -- BLAST results
    blast_fwd_off_targets INTEGER DEFAULT 0,
    blast_rev_off_targets INTEGER DEFAULT 0,
    blast_fwd_details   JSONB,
    blast_rev_details   JSONB,
    
    -- Validation status
    -- 'computational': designed and scored by agent
    -- 'wet_lab_validated': experimentally confirmed
    -- 'published': included in a publication
    -- 'deprecated': replaced by better design
    validation_status   VARCHAR(30) DEFAULT 'computational',
    
    -- Confidence assessment
    confidence_score    REAL,
    confidence_level    VARCHAR(20),  -- 'HIGH', 'MODERATE', 'LOW', 'VERY_LOW'
    confidence_reasoning TEXT,
    
    -- Experiment metadata
    experiment_notes    TEXT,
    pcr_conditions      JSONB,       -- Recommended PCR conditions
    
    -- Score breakdown (JSONB)
    score_breakdown     JSONB,
    failure_details     TEXT[]        -- Array of failure reason strings
);

-- ============================================================================
-- Indexes for common query patterns
-- ============================================================================
CREATE INDEX IF NOT EXISTS idx_designs_gene ON primer_designs(gene_symbol);
CREATE INDEX IF NOT EXISTS idx_designs_organism ON primer_designs(organism);
CREATE INDEX IF NOT EXISTS idx_designs_score ON primer_designs(quality_score DESC);
CREATE INDEX IF NOT EXISTS idx_designs_status ON primer_designs(validation_status);
CREATE INDEX IF NOT EXISTS idx_designs_session ON primer_designs(session_id);
CREATE INDEX IF NOT EXISTS idx_designs_accession ON primer_designs(accession_id);
CREATE INDEX IF NOT EXISTS idx_designs_application ON primer_designs(application);

CREATE INDEX IF NOT EXISTS idx_sessions_gene ON design_sessions(gene_symbol);
CREATE INDEX IF NOT EXISTS idx_sessions_organism ON design_sessions(organism);
CREATE INDEX IF NOT EXISTS idx_sessions_status ON design_sessions(status);

-- ============================================================================
-- Views for common queries
-- ============================================================================

-- View: Top primer designs per gene
CREATE OR REPLACE VIEW top_primers_per_gene AS
SELECT DISTINCT ON (gene_symbol, organism)
    id, gene_symbol, organism, application,
    fwd_sequence, rev_sequence,
    fwd_tm, rev_tm, fwd_gc, rev_gc,
    amplicon_length, quality_score,
    confidence_score, validation_status,
    created_at
FROM primer_designs
WHERE quality_score >= 70
ORDER BY gene_symbol, organism, quality_score DESC;

-- View: Database statistics
CREATE OR REPLACE VIEW database_stats AS
SELECT
    COUNT(*) AS total_designs,
    COUNT(*) FILTER (WHERE quality_score >= 70) AS passed_designs,
    ROUND(AVG(quality_score)::numeric, 1) AS avg_score,
    COUNT(DISTINCT gene_symbol) AS unique_genes,
    COUNT(DISTINCT organism) AS unique_organisms,
    COUNT(*) FILTER (WHERE validation_status = 'wet_lab_validated') AS wet_lab_validated
FROM primer_designs;
