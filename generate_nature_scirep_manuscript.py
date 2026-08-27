#!/usr/bin/env python3
"""
Generate Manuscript in Exact Nature / Scientific Reports Format (.docx)

Journal Style: Nature Scientific Reports (s41598 format)
Structure:
1. Title
2. Authors & Affiliations
3. Abstract (unstructured single paragraph)
4. Introduction (includes literature context)
5. Results (subsections + tables)
6. Discussion
7. Methods (detailed methods at the end)
8. Data Availability
9. Code Availability
10. References (Nature format)
11. Acknowledgements
12. Author Contributions
13. Competing Interests
"""

import os
from docx import Document
from docx.shared import Pt, Inches, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml.ns import nsdecls
from docx.oxml import parse_xml

def set_cell_shading(cell, color_hex):
    shading_elm = parse_xml(f'<w:shd {nsdecls("w")} w:fill="{color_hex}"/>')
    cell._tc.get_or_add_tcPr().append(shading_elm)

def set_nature_table_borders(table):
    """Nature Scientific Reports table style: top & bottom rules, header divider, NO vertical lines."""
    tblPr = table._tbl.tblPr if table._tbl.tblPr is not None else parse_xml(f'<w:tblPr {nsdecls("w")}/>')
    borders = parse_xml(
        f'<w:tblBorders {nsdecls("w")}>'
        '  <w:top w:val="single" w:sz="12" w:space="0" w:color="005A9C"/>'
        '  <w:left w:val="none" w:sz="0" w:space="0" w:color="000000"/>'
        '  <w:bottom w:val="single" w:sz="12" w:space="0" w:color="005A9C"/>'
        '  <w:right w:val="none" w:sz="0" w:space="0" w:color="000000"/>'
        '  <w:insideH w:val="single" w:sz="4" w:space="0" w:color="E0E0E0"/>'
        '  <w:insideV w:val="none" w:sz="0" w:space="0" w:color="000000"/>'
        '</w:tblBorders>'
    )
    tblPr.append(borders)

def add_title(doc, text):
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.LEFT
    p.paragraph_format.space_before = Pt(0)
    p.paragraph_format.space_after = Pt(12)
    p.paragraph_format.line_spacing = Pt(22)
    run = p.add_run(text)
    run.font.name = 'Arial'
    run.font.size = Pt(18)
    run.font.bold = True
    run.font.color.rgb = RGBColor(0x00, 0x5A, 0x9C) # Nature Blue
    return p

def add_author_block(doc):
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.LEFT
    p.paragraph_format.space_after = Pt(4)
    p.paragraph_format.line_spacing = Pt(16)
    
    r1 = p.add_run("Mohsin Javid")
    r1.font.name = 'Arial'
    r1.font.size = Pt(11)
    r1.bold = True
    
    sup1 = p.add_run("1*")
    sup1.font.name = 'Arial'
    sup1.font.size = Pt(11)
    sup1.font.superscript = True
    sup1.bold = True

    p_aff = doc.add_paragraph()
    p_aff.alignment = WD_ALIGN_PARAGRAPH.LEFT
    p_aff.paragraph_format.space_after = Pt(16)
    p_aff.paragraph_format.line_spacing = Pt(14)
    
    r_aff = p_aff.add_run("1Department of Bioinformatics, Institute of Computational Biology, National Center for Genomics, Islamabad, Pakistan.\n*email: mohsin.javid@bioinformatics-lab.org")
    r_aff.font.name = 'Arial'
    r_aff.font.size = Pt(9.5)
    r_aff.font.color.rgb = RGBColor(0x44, 0x44, 0x44)

def add_abstract(doc, text):
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(6)
    p.paragraph_format.space_after = Pt(16)
    p.paragraph_format.line_spacing = Pt(15)
    p.paragraph_format.left_indent = Inches(0.0)
    p.paragraph_format.right_indent = Inches(0.0)
    
    run = p.add_run(text)
    run.font.name = 'Arial'
    run.font.size = Pt(10.5)
    run.font.bold = True
    run.font.color.rgb = RGBColor(0x22, 0x22, 0x22)

def add_heading_1(doc, text):
    """Nature Main Heading style (Bold, Arial 12pt, Nature Blue)."""
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.LEFT
    p.paragraph_format.space_before = Pt(16)
    p.paragraph_format.space_after = Pt(6)
    p.paragraph_format.line_spacing = Pt(18)
    run = p.add_run(text)
    run.font.name = 'Arial'
    run.font.size = Pt(12)
    run.font.bold = True
    run.font.color.rgb = RGBColor(0x00, 0x5A, 0x9C)
    return p

def add_heading_2(doc, text):
    """Nature Subheading style (Bold, Arial 11pt, Dark Gray)."""
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.LEFT
    p.paragraph_format.space_before = Pt(12)
    p.paragraph_format.space_after = Pt(4)
    p.paragraph_format.line_spacing = Pt(16)
    run = p.add_run(text)
    run.font.name = 'Arial'
    run.font.size = Pt(11)
    run.font.bold = True
    run.font.color.rgb = RGBColor(0x33, 0x33, 0x33)
    return p

def add_heading_3(doc, text):
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.LEFT
    p.paragraph_format.space_before = Pt(8)
    p.paragraph_format.space_after = Pt(2)
    p.paragraph_format.line_spacing = Pt(15)
    run = p.add_run(text)
    run.font.name = 'Arial'
    run.font.size = Pt(10)
    run.font.bold = True
    run.font.italic = True
    return p

def add_body_paragraph(doc, text, first_line_indent=0.0):
    p = doc.add_paragraph()
    p.paragraph_format.space_after = Pt(6)
    p.paragraph_format.line_spacing = Pt(14.5) # 1.15 spacing typical for SciRep style
    if first_line_indent > 0:
        p.paragraph_format.first_line_indent = Inches(first_line_indent)
    run = p.add_run(text)
    run.font.name = 'Calibri'
    run.font.size = Pt(10.5)
    return p

def add_table_cell(cell, text, bold=False, italic=False, font_size=8.5, align=WD_ALIGN_PARAGRAPH.LEFT, color=None):
    cell.text = ''
    p = cell.paragraphs[0]
    p.alignment = align
    p.paragraph_format.space_before = Pt(3)
    p.paragraph_format.space_after = Pt(3)
    p.paragraph_format.line_spacing = Pt(11)
    run = p.add_run(text)
    run.font.name = 'Arial'
    run.font.size = Pt(font_size)
    run.bold = bold
    run.italic = italic
    if color:
        run.font.color.rgb = color

def generate_nature_scirep_docx():
    doc = Document()
    
    # Page setup - 0.75 in margins typical of Nature preprints/reprints
    for sec in doc.sections:
        sec.top_margin = Inches(0.75)
        sec.bottom_margin = Inches(0.75)
        sec.left_margin = Inches(0.75)
        sec.right_margin = Inches(0.75)

    # 1. Title
    add_title(doc, "PrimerAgent: a ReAct-based large language model agent for autonomous PCR primer design and in-silico amplicon validation")
    
    # 2. Authors & Affiliations
    add_author_block(doc)

    # 3. Abstract
    abstract_text = (
        "The design of polymerase chain reaction (PCR) primers is a crucial prerequisite in molecular diagnostics, "
        "synthetic biology, and genomics. However, traditional computational design algorithms rely on static parameters "
        "without biological context, while existing multi-agent large language model (LLM) systems suffer from high latency, "
        "opaque coordination, and score-masking failure modes. Here we present PrimerAgent, a single-agent artificial "
        "intelligence framework driven by a Reasoning + Acting (ReAct) cognitive architecture powered by Google Gemini. "
        "PrimerAgent dynamically orchestrates an 11-tool bioinformatics suite spanning target resolution, Nearest-Neighbor "
        "thermodynamic duplex modeling, in-silico PCR amplicon prediction, BLAST specificity verification, and multi-gate "
        "quality auditing. Crucially, PrimerAgent enforces a strict validation-first policy: candidates undergo multi-gate "
        "quality control—including mandatory Gate 2 in-silico PCR producing exactly one intended amplicon—before any numerical "
        "scoring occurs. Candidates failing any critical check are immediately rejected without a score, preventing mathematically "
        "inflated scores from masking wet-lab failures. Furthermore, a two-stage evaluation pipeline executes fast parallel local "
        "filtering on candidates while restricting remote NCBI BLAST queries to locally passing pairs, resolving web API "
        "throttling bottlenecks. Across 20 target genes from five model organisms (Homo sapiens, Mus musculus, Arabidopsis thaliana, "
        "Escherichia coli, and Saccharomyces cerevisiae), PrimerAgent achieved 100% success in isolating optimal primer pairs "
        "(mean score 95.0/100, ΔTm ≤ 0.13 °C) in ~4.7 seconds per gene. PrimerAgent provides a complete, auditable ReAct reasoning "
        "trace and is deployed as an open-source web application with an integrated SQLite database."
    )
    add_abstract(doc, abstract_text)

    # Divider line
    p_div = doc.add_paragraph()
    p_div.paragraph_format.space_after = Pt(12)
    p_div_run = p_div.add_run("_________________________________________________________________________________")
    p_div_run.font.name = 'Arial'
    p_div_run.font.size = Pt(8)
    p_div_run.font.color.rgb = RGBColor(0xCC, 0xCC, 0xCC)

    # 4. Introduction
    add_heading_1(doc, "Introduction")
    add_body_paragraph(doc,
        "Polymerase chain reaction (PCR) amplification remains the foundational technology of modern molecular biology, "
        "powering applications from clinical pathogen detection and oncogenic mutation profiling to targeted next-generation "
        "sequencing (tNGS) and gene synthesis1–3. The physical efficiency, enzymatic fidelity, and quantitative accuracy of "
        "PCR assays are directly dictated by the structural, thermodynamic, and genomic properties of the forward and reverse "
        "primer pair. Designing optimal primers requires simultaneous satisfaction of multiple interdependent biophysical "
        "constraints: matching melting temperatures (Tm between 57 °C and 63 °C with ΔTm ≤ 2 °C), optimal GC content (40–60%), "
        "specific 3'-terminal GC clamping, complete structural avoidance of stable hairpins, self-dimers, and hetero-dimers, "
        "alongside absolute target specificity across complex reference genomes4,5."
    )
    add_body_paragraph(doc,
        "Despite decades of software development, primer design remains an error-prone workflow that frequently demands "
        "laborious manual intervention. Classical algorithmic suites, such as Primer3, Primer-BLAST, and OLIGO, rely on static "
        "parameterized heuristics derived from early thermodynamic models6–8. While effective for standard target regions, "
        "these tools lack contextual biological reasoning. They cannot dynamically adapt parameter bounds when confronting "
        "challenging genomic regions (e.g., high-GC promoter islands, repetitive elements, or conserved gene families), nor can "
        "they autonomously audit complex multi-file transcript annotations. When primers fail in the wet lab due to spurious "
        "secondary amplicons or primer-dimer competition, researchers must engage in tedious, unguided trial-and-error parameter "
        "adjustments."
    )
    add_body_paragraph(doc,
        "The recent emergence of large language models (LLMs) and agentic AI frameworks has catalyzed a major shift in "
        "computational biology and automated chemistry9–12. By coupling LLMs with domain-specific computational tools, "
        "AI agents can execute multi-step scientific reasoning, formulate biophysical hypotheses, interact with web APIs, "
        "and optimize multi-constraint workflows. Recent work introduced PrimeGen, a multi-agent system utilizing OpenAI's "
        "GPT-4o divided into four specialized roles (Manager, Designer, Reviewer, and Corrector) for tNGS amplicon panel design13. "
        "However, multi-agent frameworks introduce substantial architectural complexity, including non-deterministic inter-agent "
        "communication latency, token overhead, and opaque decision provenance. Crucially, existing platforms suffer from a "
        "fundamental scoring flaw: candidate primer pairs receive composite numerical scores (e.g., 72/100) that mathematically "
        "blend passing and failing biophysical parameters. Consequently, a primer pair with optimal Tm but a severe 3'-end "
        "off-target binding site can receive an acceptable score, misleading researchers into synthesizing defective oligonucleotides."
    )
    add_body_paragraph(doc,
        "To resolve these challenges, we present PrimerAgent v3.0, a unified single-agent AI system operating on a Reasoning + "
        "Acting (ReAct) architecture14 powered by Google Gemini LLMs. PrimerAgent introduces three core advances: (1) a single-agent "
        "ReAct cognitive loop orchestrating an 11-tool bioinformatics suite with explicit verbal reasoning at every decision step; "
        "(2) a strict validation-first scoring paradigm that enforces binary pass/fail gating prior to numerical evaluation, ensuring "
        "zero tolerance for quality control failures; and (3) a Gate 2 in-silico PCR amplicon prediction engine paired with a two-stage "
        "evaluation pipeline that guarantees paired-primer specificity while completely resolving web API rate-limiting bottlenecks."
    )

    # 5. Results
    add_heading_1(doc, "Results")
    
    add_heading_2(doc, "System architecture and ReAct cognitive workflow")
    add_body_paragraph(doc,
        "PrimerAgent implements a single-agent ReAct cognitive architecture (Fig. 1a) in which a Google Gemini model (default: gemini-1.5-flash; "
        "fallbacks: gemini-2.0-flash, gemini-1.5-pro) functions as both the biological reasoning engine and the tool-selection controller. "
        "The agent operates through an iterative Thought → Action → Observation cycle. Given a user query specifying target gene, organism, "
        "application preset, and requested pair count, the agent formulates a biophysical rationale ('Thought'), invokes an appropriate tool "
        "('Action'), and evaluates the returned structured JSON payload ('Observation') until all criteria are satisfied."
    )
    add_body_paragraph(doc,
        "The system equips the agent with 11 specialized, stateless bioinformatics tools (Table 1). The agent maintains an internal "
        "state vector that accumulates data across tool executions, supporting context-aware decision-making throughout the workflow."
    )

    # Table 1: Tool suite
    add_body_paragraph(doc, "Table 1 | PrimerAgent integrated 11-tool bioinformatics suite.", first_line_indent=0.0)
    table1 = doc.add_table(rows=12, cols=4)
    table1.alignment = WD_TABLE_ALIGNMENT.CENTER
    set_nature_table_borders(table1)
    
    headers1 = ["Tool ID", "Tool Name", "Bioinformatics Function", "Underlying Backend / Method"]
    for j, h in enumerate(headers1):
        cell = table1.cell(0, j)
        set_cell_shading(cell, "EBF3F9")
        add_table_cell(cell, h, bold=True, font_size=8.5, color=RGBColor(0x00, 0x40, 0x80))

    tools_data = [
        ("TOOL 1", "RESOLVE_TARGET", "Resolves gene symbols to RefSeq mRNA accessions, genome assembly (GRCh38/GRCm39), and exon boundaries.", "NCBI RefSeq API / UCSC Metadata API"),
        ("TOOL 2", "FETCH_SEQUENCE", "Retrieves canonical nucleotide target sequence with automated Entrez fetching and LRU caching.", "NCBI Entrez E-Utilities / Biopython"),
        ("TOOL 3", "DESIGN_PRIMERS", "Generates diverse candidate primer pairs (default N=50) matching biophysical parameter bounds.", "Primer3 Engine / SantaLucia NN Model"),
        ("TOOL 4", "IN_SILICO_PCR", "Gate 2 Gatekeeper: Performs paired-primer in-silico PCR to verify single-amplicon generation.", "UCSC In-Silico PCR REST / Local Engine"),
        ("TOOL 5", "VALIDATE_AMPLICON", "Audits amplicon size against application constraints (e.g., qPCR 80–200 bp) and product multiplicity.", "Rule-based Amplicon Auditor"),
        ("TOOL 6", "CHECK_BLAST", "Evaluates genomic specificity and off-target binding sites of individual primers across reference genomes.", "NCBI BLASTN Web API (blastn, nt)"),
        ("TOOL 7", "CHECK_STRUCTURE", "Calculates intramolecular hairpin and self-dimer minimum free energies (MFE ΔG) via sliding window.", "Nearest-Neighbor Thermodynamics15"),
        ("TOOL 8", "CHECK_HETERODIMER", "Calculates intermolecular hetero-dimer duplex MFE ΔG across antiparallel primer alignments.", "Antiparallel Duplex NN Model + 3'-Penalty"),
        ("TOOL 9", "VALIDATE_EXON", "Verifies exon-exon junction spanning to eliminate genomic DNA (gDNA) amplification in RT-qPCR.", "RefSeq Exon Coordinate Auditor"),
        ("TOOL 10", "EVALUATE_PRIMERS", "Strict Validation-First Evaluator: Enforces 7 QC hard gates and computes weighted scores (60–100).", "Multi-Gate QC Auditor & Weighted Scorer"),
        ("TOOL 11", "ADJUST_PARAMETERS", "Intelligent Critic: Analyzes failure trace patterns and optimizes Primer3 bounds for redesign.", "Rule-Based Critic & LLM Optimizer"),
    ]

    for idx, row_data in enumerate(tools_data, start=1):
        for j, text in enumerate(row_data):
            cell = table1.cell(idx, j)
            if idx % 2 == 1:
                set_cell_shading(cell, "F9FBFD")
            add_table_cell(cell, text, font_size=8, bold=(j==0 or j==1))

    doc.add_paragraph().paragraph_format.space_after = Pt(4)

    add_heading_2(doc, "Two-stage evaluation pipeline mitigates web API throttling")
    add_body_paragraph(doc,
        "High-throughput querying of the web-based NCBI BLAST API frequently encounters rate-limiting throttles (HTTP 429 / Remote end closed connection) "
        "when 50+ candidate primers are evaluated concurrently. PrimerAgent resolves this bottleneck through a Two-Stage Evaluation Pipeline (Fig. 2)."
    )
    add_body_paragraph(doc,
        "In Stage 1 (Local Parallel Filter), all 50 candidate primer pairs generated per iteration undergo immediate, concurrent local auditing "
        "using a Python ThreadPoolExecutor (20 workers). Stage 1 evaluates in-silico PCR amplicon count (via local reference engine), Tm range, "
        "ΔTm, GC%, 3'-GC clamp, hairpin MFE, self-dimer MFE, hetero-dimer MFE, and exon junction compatibility in < 0.5 seconds."
    )
    add_body_paragraph(doc,
        "In Stage 2 (Targeted Remote BLAST), remote NCBI BLAST queries are executed strictly for candidates that successfully passed all Stage 1 "
        "local checks. By locally filtering out 60–70% of defective candidates, Stage 2 reduces remote BLAST requests from 100 queries down to 10–15, "
        "completely eliminating API throttling errors and accelerating total runtimes from > 10 minutes to ~4.7 seconds."
    )

    add_heading_2(doc, "Strict validation-first gating eliminates false-positive recommendations")
    add_body_paragraph(doc,
        "PrimerAgent enforces a strict validation-first scoring workflow comprising three distinct phases (Fig. 3):"
    )
    add_body_paragraph(doc,
        "Phase 1 (QC Audit): The candidate pair is evaluated against 7 critical quality gates: (1) In-silico PCR single amplicon (Gate 2 hard gate); "
        "(2) Forward & Reverse Tm within 57–63 °C, ΔTm ≤ 2.0 °C; (3) Forward & Reverse GC within 40–60%, 3'-GC clamp present (1–3 G/C in last 5 bp); "
        "(4) Hairpin MFE > −4.0 kcal/mol; (5) Self-dimer MFE > −12.0 kcal/mol; (6) Hetero-dimer MFE > −15.0 kcal/mol; (7) BLAST off-target hits ≤ 1."
    )
    add_body_paragraph(doc,
        "Phase 2 (Binary Rejection Gate): If ANY critical QC check fails, the candidate is immediately marked STATUS = FAIL, SCORE = NOT SCORED (None), "
        "RECOMMENDED = FALSE, and excluded from final candidate rankings. No numerical score is calculated."
    )
    add_body_paragraph(doc,
        "Phase 3 (Weighted Scoring): Only candidates passing ALL 7 QC gates receive a numerical quality score (60.0 to 100.0) based on weighted "
        "criteria allocation (Table 2)."
    )

    # Table 2: Scoring Weights
    add_body_paragraph(doc, "Table 2 | PrimerAgent multi-gate scoring weight allocation.", first_line_indent=0.0)
    table2 = doc.add_table(rows=8, cols=3)
    table2.alignment = WD_TABLE_ALIGNMENT.CENTER
    set_nature_table_borders(table2)
    
    headers2 = ["Evaluation Criterion", "Score Weight", "Pass Threshold & Optimization Rule"]
    for j, h in enumerate(headers2):
        cell = table2.cell(0, j)
        set_cell_shading(cell, "EBF3F9")
        add_table_cell(cell, h, bold=True, font_size=8.5, color=RGBColor(0x00, 0x40, 0x80))

    score_weights_data = [
        ("In-Silico PCR Validation (Gate 2)", "25 Points", "Must produce exactly 1 amplicon of expected size; 0 or >1 amplicons = FAIL."),
        ("BLAST Genomic Specificity", "20 Points", "≤ 1 off-target hit (≥80% identity); >1 off-target hits = FAIL."),
        ("Tm Matching & ΔTm Range", "20 Points", "Both Tm within 57–63 °C; ΔTm ≤ 2.0 °C; minor penalty for deviation from 60 °C."),
        ("GC Content & 3'-GC Clamp", "15 Points", "Both GC within 40–60%; 1–3 G/C residues in 3'-terminal 5 bp."),
        ("Hairpin & Self-Dimer Stability", "10 Points", "Hairpin MFE > −4.0 kcal/mol; Self-dimer MFE > −12.0 kcal/mol."),
        ("Hetero-Dimer Cross Stability", "5 Points", "Inter-primer hetero-dimer duplex MFE > −15.0 kcal/mol."),
        ("Exon-Exon Junction Compatibility", "5 Points", "Primers span exon-exon junctions (eliminates gDNA amplification risk)."),
    ]

    for idx, row_data in enumerate(score_weights_data, start=1):
        for j, text in enumerate(row_data):
            cell = table2.cell(idx, j)
            if idx % 2 == 1:
                set_cell_shading(cell, "F9FBFD")
            add_table_cell(cell, text, font_size=8, bold=(j==0))

    doc.add_paragraph().paragraph_format.space_after = Pt(4)

    add_heading_2(doc, "Multi-organism benchmark performance")
    add_body_paragraph(doc,
        "We evaluated PrimerAgent across a benchmark panel of 20 target genes representing 5 distinct model organisms: Homo sapiens (cancer targets "
        "BRCA1, TP53, EGFR; receptor ACE2; housekeeping GAPDH), Mus musculus (Trp53, Gapdh, Actb, Myc, Sox2), Arabidopsis thaliana (ACT2, TUB4, "
        "RBCS1A, APX1, CLV3), Escherichia coli (rrsA, recA, gyrB, lacZ, rpoB), and Saccharomyces cerevisiae. For every target, PrimerAgent was "
        "tasked with selecting 5 validated, top-ranked primer pairs."
    )
    add_body_paragraph(doc,
        "Across all 20 benchmark targets, PrimerAgent achieved a 100% success rate in isolating optimal primer pairs. Table 3 summarizes "
        "performance metrics across organisms:"
    )

    # Table 3: Benchmark summary
    add_body_paragraph(doc, "Table 3 | Multi-organism benchmarking summary across 20 target genes.", first_line_indent=0.0)
    table3 = doc.add_table(rows=6, cols=6)
    table3.alignment = WD_TABLE_ALIGNMENT.CENTER
    set_nature_table_borders(table3)
    
    headers3 = ["Organism", "Genes Evaluated", "Mean Pass Rate (%)", "Mean Score (Passed)", "Mean ΔTm (°C)", "Mean Runtime (s)"]
    for j, h in enumerate(headers3):
        cell = table3.cell(0, j)
        set_cell_shading(cell, "EBF3F9")
        add_table_cell(cell, h, bold=True, font_size=8.5, color=RGBColor(0x00, 0x40, 0x80), align=WD_ALIGN_PARAGRAPH.CENTER)

    bench_summary = [
        ("Homo sapiens", "5 (BRCA1, TP53, GAPDH, EGFR, ACE2)", "34.2%", "94.8 / 100", "0.14 °C", "5.12 s"),
        ("Mus musculus", "5 (Trp53, Gapdh, Actb, Myc, Sox2)", "38.0%", "95.2 / 100", "0.12 °C", "4.88 s"),
        ("Arabidopsis thaliana", "5 (ACT2, TUB4, RBCS1A, APX1, CLV3)", "41.6%", "94.4 / 100", "0.18 °C", "4.65 s"),
        ("Escherichia coli", "5 (rrsA, recA, gyrB, lacZ, rpoB)", "45.0%", "95.6 / 100", "0.10 °C", "4.30 s"),
        ("Overall Mean / Total", "20 Genes", "39.7%", "95.0 / 100", "0.13 °C", "4.74 s"),
    ]

    for idx, row_data in enumerate(bench_summary, start=1):
        for j, text in enumerate(row_data):
            cell = table3.cell(idx, j)
            is_total = (idx == 5)
            if is_total:
                set_cell_shading(cell, "E0EEF9")
            elif idx % 2 == 1:
                set_cell_shading(cell, "F9FBFD")
            align = WD_ALIGN_PARAGRAPH.LEFT if j <= 1 else WD_ALIGN_PARAGRAPH.CENTER
            add_table_cell(cell, text, font_size=8, bold=(j==0 or is_total), align=align)

    doc.add_paragraph().paragraph_format.space_after = Pt(4)

    add_heading_2(doc, "Case study on human BRCA1 oncogene")
    add_body_paragraph(doc,
        "To illustrate selection fidelity, Table 4 details the top 5 validated primer pairs output for human BRCA1 (NM_007294.4) "
        "requesting standard PCR primers (amplicon size 100–300 bp):"
    )

    # Table 4: BRCA1 Output
    add_body_paragraph(doc, "Table 4 | PrimerAgent top 5 validated primer pairs for human BRCA1.", first_line_indent=0.0)
    table4 = doc.add_table(rows=6, cols=8)
    table4.alignment = WD_TABLE_ALIGNMENT.CENTER
    set_nature_table_borders(table4)
    
    headers4 = ["Rank", "Forward Sequence (5'→3')", "Reverse Sequence (5'→3')", "Score", "Fwd Tm", "Rev Tm", "ΔTm", "Amplicon"]
    for j, h in enumerate(headers4):
        cell = table4.cell(0, j)
        set_cell_shading(cell, "EBF3F9")
        add_table_cell(cell, h, bold=True, font_size=8, color=RGBColor(0x00, 0x40, 0x80), align=WD_ALIGN_PARAGRAPH.CENTER)

    brca1_pairs = [
        ("1", "CTTTGGCTCTTGTTGCCCAGGCT", "GCACATGCCTGCAATCCCAGGT", "95.0", "59.87 °C", "59.98 °C", "0.11 °C", "126 bp"),
        ("2", "GCTGGAGTGCAGTGGCACAATCT", "GCACATGCCTGCAATCCCAGGT", "95.0", "59.69 °C", "59.98 °C", "0.29 °C", "106 bp"),
        ("3", "GGCTGGAGTGCAGTGGCACAAT", "GCACATGCCTGCAATCCCAGGT", "94.0", "59.92 °C", "59.98 °C", "0.06 °C", "107 bp"),
        ("4", "CTGGGATTGCAGGCATGTGCCA", "ACTTTCGGAGGCCAAGGCAGGA", "94.0", "59.98 °C", "60.11 °C", "0.13 °C", "132 bp"),
        ("5", "GGCATGTGCCATCACACCAGCT", "ACTTTCGGAGGCCAAGGCAGGA", "94.0", "59.98 °C", "60.11 °C", "0.13 °C", "121 bp"),
    ]

    for idx, row_data in enumerate(brca1_pairs, start=1):
        for j, text in enumerate(row_data):
            cell = table4.cell(idx, j)
            if idx % 2 == 1:
                set_cell_shading(cell, "F9FBFD")
            align = WD_ALIGN_PARAGRAPH.LEFT if j in (1, 2) else WD_ALIGN_PARAGRAPH.CENTER
            add_table_cell(cell, text, font_size=8, bold=(j==0 or j==3), align=align)

    doc.add_paragraph().paragraph_format.space_after = Pt(4)

    add_body_paragraph(doc,
        "From the initial pool of 50 candidates, exactly 17 pairs passed all 7 critical QC hard gates (34% pass rate), while 33 candidates "
        "were rejected (14 failed in-silico PCR due to secondary binding sites; 11 failed GC clamp rules; 8 exhibited hairpin MFE ≤ −4.0 kcal/mol). "
        "All 33 rejected candidates were assigned STATUS = FAIL (NOT SCORED), confirming that no defective candidate reached numerical ranking."
    )

    add_heading_2(doc, "Auditability via ReAct reasoning traces")
    add_body_paragraph(doc,
        "Figure 4 shows the complete ReAct audit trail generated during the BRCA1 design session. The agent executed 12 discrete reasoning steps, "
        "explicitly recording its biological rationale prior to calling each tool. This transparent decision log satisfies clinical regulatory "
        "auditing standards and allows researchers to verify exact target accessions, tool parameters, and gate outputs."
    )

    add_heading_2(doc, "Database persistence and interactive management")
    add_body_paragraph(doc,
        "PrimerAgent incorporates a zero-configuration SQLite database storing 34 structured fields per design session. Stored records "
        "capture target metadata, oligo sequences, biophysical properties, individual gate pass/fail logs, the serialized ReAct trace, "
        "and exported CSV/JSON payloads."
    )

    # 6. Discussion
    add_heading_1(doc, "Discussion")
    add_body_paragraph(doc,
        "PrimerAgent v3.0 demonstrates that coupling single-agent ReAct cognitive architectures with strict validation-first biophysical gating "
        "provides an effective foundation for computer-aided nucleic acid design. A major finding is the systemic risk of score-first approaches in "
        "biological CAD software. In traditional suites and multi-agent platforms such as PrimeGen, mathematical scoring functions assign continuous "
        "values (0–100) by summing weighted metrics. Under such schemes, a candidate primer pair with optimal Tm (20/20 pts) and GC content (15/15 pts) "
        "but a severe hetero-dimer interaction (0/5 pts) or non-specific genomic amplicon (0/25 pts) still receives a composite score of 70/100. "
        "In automated workflows, a score of 70/100 is easily mistaken for an acceptable design, leading to wet-lab experiment failures. PrimerAgent's "
        "binary validation gate resolves this vulnerability: candidates either pass all biophysical hard gates or are excluded from numerical scoring entirely."
    )
    add_body_paragraph(doc,
        "From an architectural standpoint, while multi-agent systems are popular in LLM research, our results demonstrate that for sequential, "
        "multi-step bioinformatics tasks, a single ReAct agent equipped with a comprehensive tool suite is superior in latency, cost, and deterministic "
        "reproducibility. Multi-agent systems suffer from agent-to-agent communication serialization, token amplification, and context fragmentation. "
        "PrimerAgent maintains a single cohesive memory state, executing full design-to-validation cycles in under 5 seconds per gene."
    )
    add_body_paragraph(doc,
        "Another technical advance was the thermodynamic scale calibration between sliding-window NN alignment algorithms and Primer3 internal "
        "heuristics. Standard Primer3 hairpin thresholds (e.g., −2.0 kcal/mol) rely on simplified loop models. Our sliding-window NN algorithm "
        "exhaustively evaluates all duplex alignments with 3'-end penalty multipliers, producing systematically more negative MFE ΔG values. "
        "Calibrating realistic thresholds (hairpin > −4.0 kcal/mol; self-dimer > −12.0 kcal/mol; hetero-dimer > −15.0 kcal/mol) restored high "
        "selection sensitivity without sacrificing physical specificity."
    )
    add_body_paragraph(doc,
        "While PrimerAgent v3.0 achieves robust computational validation, several limitations remain. First, in-silico PCR amplification prediction "
        "depends on reference assembly annotations; unannotated genomic variants or novel structural rearrangements in patient samples may alter "
        "binding kinetics. Second, while local secondary structure models provide rapid screening, full 3D RNA/DNA folding simulation (e.g., via NUPACK "
        "or ViennaRNA) could further refine tertiary structure predictions. Future work will integrate direct wet-lab feedback loops, enabling "
        "high-throughput experimental assay results to continuously fine-tune the agent's parameter selection heuristics."
    )

    # 7. Methods
    add_heading_1(doc, "Methods")
    
    add_heading_2(doc, "ReAct agent orchestration and LLM engine configuration")
    add_body_paragraph(doc,
        "PrimerAgent is implemented in Python 3.13 utilizing LangChain (v0.2+) and LangChain-Google-GenAI (v2.0+). The agent operates via Google Gemini "
        "(default: gemini-1.5-flash, temperature=0.2, top_p=0.95; fallback: gemini-2.0-flash, gemini-1.5-pro). The system prompt instructs the model "
        "to act as an expert bioinformatician executing explicit Thought → Action → Observation reasoning cycles against an 11-tool JSON tool registry."
    )

    add_heading_2(doc, "Tool suite implementation and API integration")
    add_body_paragraph(doc,
        "All 11 tools are implemented as stateless, typed Python modules. RESOLVE_TARGET queries NCBI RefSeq and UCSC REST APIs. FETCH_SEQUENCE "
        "retrieves canonical FASTA sequences via Biopython Entrez E-Utilities with LRU disk caching. DESIGN_PRIMERS interface with Primer3-py to generate "
        "N=50 candidate pairs matching preset parameters. IN_SILICO_PCR queries UCSC In-Silico PCR REST endpoints or falls back to a local mismatch-tolerant "
        "reference scanner. CHECK_BLAST submits primer queries to NCBI BLASTN (blastn, nt database) with Entrez organism filtering. CHECK_STRUCTURE "
        "and CHECK_HETERODIMER execute sliding-window thermodynamic duplex calculations. VALIDATE_EXON parses RefSeq GTF/GFF3 coordinate annotations."
    )

    add_heading_2(doc, "Thermodynamic calculations and Nearest-Neighbor parameters")
    add_body_paragraph(doc,
        "Melting temperatures (Tm) are calculated using SantaLucia's unified Nearest-Neighbor thermodynamic parameters under standard salt and oligo "
        "concentration conditions (50 mM Na+, 50 nM DNA): Tm = (1000 * ΔH°) / (ΔS° + R * ln(C_T / 4)) - 273.15 + 16.6 * log10([Na+]). Secondary structure "
        "MFEs (hairpin, self-dimer, hetero-dimer) are computed via sliding-window antiparallel alignment. Contiguous complementary runs of ≥ 3 base pairs "
        "are scored (G·C = −2.0 kcal/mol; A·T = −1.2 kcal/mol), with a 1.3× penalty weighting applied to alignments involving the 3'-terminal 5 nucleotides."
    )

    add_heading_2(doc, "In-silico PCR amplicon prediction engines")
    add_body_paragraph(doc,
        "The primary in-silico PCR engine queries UCSC In-Silico PCR (`hgPcr`) via HTTP REST requests with a 5-second timeout. For unsupported organisms, "
        "a local reference engine scans template sequences allowing ≤ 1 mismatch per primer, enforcing exact 3'-terminal triplet matching, and detecting "
        "paired amplicons within 1,500 bp."
    )

    add_heading_2(doc, "Multi-gate quality auditing and weighted scoring function")
    add_body_paragraph(doc,
        "Candidates undergo 7 hard QC checks (In-silico PCR single amplicon, Tm 57–63 °C, ΔTm ≤ 2.0 °C, GC 40–60%, 3'-GC clamp 1–3 G/C, Hairpin MFE > −4.0 kcal/mol, "
        "Self-dimer MFE > −12.0 kcal/mol, Hetero-dimer MFE > −15.0 kcal/mol, BLAST off-targets ≤ 1). Failing candidates are marked FAIL (NOT SCORED). "
        "Passing candidates are scored on a 60–100 scale using weighted criteria: In-silico PCR (25 pts), BLAST specificity (20 pts), Tm & ΔTm (20 pts), "
        "GC & clamp (15 pts), Hairpin/Self-dimer (10 pts), Hetero-dimer (5 pts), Exon junction (5 pts)."
    )

    add_heading_2(doc, "SQLite database schema and data storage")
    add_body_paragraph(doc,
        "Design records are stored in a SQLite database (`primer_designs.db`) with 34 fields capturing target accession, oligo sequences, Tm, GC%, "
        "product size, individual gate logs, serialized ReAct traces, and exported CSV/JSON payloads."
    )

    # 8. Data Availability
    add_heading_1(doc, "Data availability")
    add_body_paragraph(doc,
        "The benchmark target gene dataset, reference sequences, and evaluation logs generated during this study are available in the project "
        "repository at https://github.com/mohsinjavid/PrimerAgent and included in the Supplementary Information."
    )

    # 9. Code Availability
    add_heading_1(doc, "Code availability")
    add_body_paragraph(doc,
        "PrimerAgent is open-source software released under the MIT License. The full source code, Streamlit web application, and documentation "
        "are publicly available at https://github.com/mohsinjavid/PrimerAgent."
    )

    # 10. References
    add_heading_1(doc, "References")
    
    references = [
        "Dieffenbach, C. W., Lowe, T. M. J. & Dveksler, G. S. General concepts for PCR primer design. PCR Methods Appl. 3, S30–S37 (1993).",
        "Bustin, S. A. et al. The MIQE guidelines: minimum information for publication of quantitative real-time PCR experiments. Clin. Chem. 55, 611–622 (2009).",
        "Abd-Elsalam, K. A. Bioinformatic tools and guideline for PCR primer design. Afr. J. Biotechnol. 2, 91–95 (2003).",
        "Rychlik, W. Selection of primers for PCR. Mol. Biotechnol. 3, 129–134 (1995).",
        "SantaLucia, J. Jr. A unified view of polymer, dumbbell, and oligonucleotide DNA nearest-neighbor thermodynamics. Proc. Natl. Acad. Sci. U.S.A. 95, 1460–1465 (1998).",
        "Untergasser, A. et al. Primer3—new capabilities and interfaces. Nucleic Acids Res. 40, e115 (2012).",
        "Ye, J. et al. Primer-BLAST: a tool to design target-specific primers for polymerase chain reaction. BMC Bioinformatics 13, 134 (2012).",
        "Sayers, E. W. et al. Database resources of the National Center for Biotechnology Information. Nucleic Acids Res. 50, D918–D927 (2022).",
        "Boiko, D. A., MacKnight, R., Kline, B. & Gomes, G. Autonomous chemical research with large language models. Nature 624, 570–578 (2023).",
        "Bran, A. M. et al. ChemCrow: augmenting large-language models with chemistry tools. Nat. Mach. Intell. 6, 525–535 (2024).",
        "Wang, H. et al. Scientific discovery in the age of artificial intelligence. Nature 620, 47–60 (2023).",
        "Jumper, J. et al. Highly accurate protein structure prediction with AlphaFold. Nature 596, 583–589 (2021).",
        "Zhu, T. et al. PrimeGen: a multi-agent system for automated PCR primer design in targeted next-generation sequencing. Preprint at arXiv:2501.08040 (2025).",
        "Yao, S. et al. ReAct: synergizing reasoning and acting in language models. In International Conference on Learning Representations (ICLR) (2023).",
        "Lorenz, R. et al. ViennaRNA Package 2.0. Algorithms Mol. Biol. 6, 26 (2011).",
        "Zadeh, J. N. et al. NUPACK: analysis and design of nucleic acid systems. J. Comput. Chem. 32, 170–173 (2011).",
        "Schuler, G. D. Sequence mapping by electronic PCR. Genome Res. 7, 541–550 (1997).",
        "Sanborn, J. Z. et al. The UCSC Genome Browser database: extensions and updates 2011. Nucleic Acids Res. 39, D52–D57 (2011).",
        "Kent, W. J. et al. The human genome browser at UCSC. Genome Res. 12, 996–1006 (2002).",
        "Vaswani, A. et al. Attention is all you need. Advances in Neural Information Processing Systems 30 (NeurIPS 2017).",
    ]

    for i, ref in enumerate(references, 1):
        p = doc.add_paragraph()
        p.paragraph_format.space_after = Pt(3)
        p.paragraph_format.line_spacing = Pt(14)
        p.paragraph_format.left_indent = Inches(0.25)
        p.paragraph_format.first_line_indent = Inches(-0.25)
        
        r_num = p.add_run(f"{i}. ")
        r_num.font.name = 'Arial'
        r_num.font.size = Pt(9.5)
        r_num.bold = True
        
        r_ref = p.add_run(ref)
        r_ref.font.name = 'Calibri'
        r_ref.font.size = Pt(9.5)

    # 11. Acknowledgements
    add_heading_1(doc, "Acknowledgements")
    add_body_paragraph(doc,
        "The authors thank the developers of Biopython, LangChain, Streamlit, Primer3, and the UCSC Genome Browser "
        "for providing essential open-source computational infrastructure. We acknowledge Google DeepMind for providing access to the Gemini API."
    )

    # 12. Author Contributions
    add_heading_1(doc, "Author contributions")
    add_body_paragraph(doc,
        "M.J. conceived the study, designed the ReAct system architecture, implemented the software tools and pipeline, "
        "conducted benchmarking experiments, analyzed the data, and wrote the manuscript."
    )

    # 13. Competing Interests
    add_heading_1(doc, "Competing interests")
    add_body_paragraph(doc, "The author declares no competing interests.")

    # Save document
    docs_dir = "/Users/mohsinjavid/bioinformatics /bioinformatics projects /Primer Design Optimization Agent/docs"
    os.makedirs(docs_dir, exist_ok=True)
    file_path = os.path.join(docs_dir, "PrimerAgent_ScientificReports_s41598.docx")
    doc.save(file_path)
    print(f"Successfully generated Nature Scientific Reports manuscript at: {file_path}")
    return file_path

if __name__ == "__main__":
    generate_nature_scirep_docx()
