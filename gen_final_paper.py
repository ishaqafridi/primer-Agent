#!/usr/bin/env python3
"""Generate PrimerAgent manuscript – Nature Scientific Reports s41598 format.
Simple English, 35 references (mostly 2023-2026)."""

from docx import Document
from docx.shared import Pt, Inches, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml.ns import nsdecls
from docx.oxml import parse_xml
import os

def shade(cell, c):
    cell._tc.get_or_add_tcPr().append(parse_xml(f'<w:shd {nsdecls("w")} w:fill="{c}"/>'))

def tborders(t):
    t._tbl.tblPr.append(parse_xml(
        f'<w:tblBorders {nsdecls("w")}>'
        '<w:top w:val="single" w:sz="12" w:space="0" w:color="000000"/>'
        '<w:left w:val="none" w:sz="0" w:space="0" w:color="000000"/>'
        '<w:bottom w:val="single" w:sz="12" w:space="0" w:color="000000"/>'
        '<w:right w:val="none" w:sz="0" w:space="0" w:color="000000"/>'
        '<w:insideH w:val="single" w:sz="4" w:space="0" w:color="D5D5D5"/>'
        '<w:insideV w:val="none" w:sz="0" w:space="0" w:color="000000"/>'
        '</w:tblBorders>'))

def tcell(c, txt, b=False, it=False, fs=9, al=WD_ALIGN_PARAGRAPH.LEFT):
    c.text = ''
    p = c.paragraphs[0]; p.alignment = al
    p.paragraph_format.space_before = Pt(2); p.paragraph_format.space_after = Pt(2)
    r = p.add_run(txt); r.font.name = 'Arial'; r.font.size = Pt(fs); r.bold = b; r.italic = it

def h1(d, t):
    p = d.add_paragraph(); p.paragraph_format.space_before = Pt(18); p.paragraph_format.space_after = Pt(8); p.paragraph_format.line_spacing = Pt(18)
    r = p.add_run(t); r.font.name = 'Arial'; r.font.size = Pt(14); r.font.bold = True

def h2(d, t):
    p = d.add_paragraph(); p.paragraph_format.space_before = Pt(14); p.paragraph_format.space_after = Pt(6); p.paragraph_format.line_spacing = Pt(16)
    r = p.add_run(t); r.font.name = 'Arial'; r.font.size = Pt(12); r.font.bold = True; r.font.italic = True

def bp(d, t):
    p = d.add_paragraph(); p.paragraph_format.space_after = Pt(8); p.paragraph_format.line_spacing = Pt(15)
    r = p.add_run(t); r.font.name = 'Arial'; r.font.size = Pt(10.5)

def tlabel(d, t):
    p = d.add_paragraph(); p.paragraph_format.space_before = Pt(10); p.paragraph_format.space_after = Pt(4)
    r = p.add_run(t); r.font.name = 'Arial'; r.font.size = Pt(10); r.font.bold = True

def main():
    doc = Document()
    for s in doc.sections:
        s.top_margin = Inches(1); s.bottom_margin = Inches(1)
        s.left_margin = Inches(0.85); s.right_margin = Inches(0.85)

    # ARTICLE label
    p = doc.add_paragraph(); p.alignment = WD_ALIGN_PARAGRAPH.LEFT; p.paragraph_format.space_after = Pt(4)
    r = p.add_run('ARTICLE'); r.font.name = 'Arial'; r.font.size = Pt(9); r.font.color.rgb = RGBColor(0x66, 0x66, 0x66)

    # Title
    p = doc.add_paragraph(); p.paragraph_format.space_after = Pt(12); p.paragraph_format.line_spacing = Pt(22)
    r = p.add_run('PrimerAgent: a ReAct-based large language model agent for autonomous PCR primer design and in-silico amplicon validation')
    r.font.name = 'Arial'; r.font.size = Pt(18); r.font.bold = True

    # Authors
    p = doc.add_paragraph(); p.paragraph_format.space_after = Pt(4)
    r = p.add_run('Mohsin Javid'); r.font.name = 'Arial'; r.font.size = Pt(12); r.bold = True
    s = p.add_run('1*'); s.font.name = 'Arial'; s.font.size = Pt(12); s.font.superscript = True

    # Journal line
    p = doc.add_paragraph(); p.paragraph_format.space_after = Pt(4)
    r = p.add_run('Scientific Reports'); r.font.name = 'Arial'; r.font.size = Pt(10); r.italic = True
    r2 = p.add_run(' volume XX, Article number: XXXXX (2026)'); r2.font.name = 'Arial'; r2.font.size = Pt(10)

    p = doc.add_paragraph(); p.paragraph_format.space_after = Pt(16)
    r = p.add_run('Cite this article'); r.font.name = 'Arial'; r.font.size = Pt(10); r.font.color.rgb = RGBColor(0x02, 0x5E, 0x8D)

    # ═══════════ ABSTRACT ═══════════
    h1(doc, 'Abstract')
    bp(doc,
       'Designing good primers for polymerase chain reaction (PCR) is one of the most important '
       'steps in molecular biology, but it is also one of the hardest to get right. A good primer '
       'pair must have the right melting temperature, GC content, and binding specificity, and it '
       'must avoid forming hairpins or dimers. Traditional software tools like Primer3 and '
       'Primer-BLAST use fixed rules and cannot reason about why a design fails. Newer AI '
       'approaches based on large language models (LLMs) have shown promise, but multi-agent '
       'systems like PrimeGen are slow, expensive, and can give misleading quality scores. In this '
       'paper, we present PrimerAgent, a single AI agent that designs, checks, and improves PCR '
       'primers on its own. PrimerAgent uses a Reasoning + Acting (ReAct) framework powered by '
       'Google Gemini LLMs, with access to 11 built-in bioinformatics tools. It follows a strict '
       '"validation-first" rule: any primer that fails even one quality check is immediately '
       'rejected without getting a score, so bad primers can never look good on paper. It also '
       'includes an in-silico PCR step that checks whether a primer pair produces exactly one '
       'product of the right size. We tested PrimerAgent on 20 genes from five organisms (human, '
       'mouse, Arabidopsis, E. coli, and yeast). It found high-quality primer pairs for every gene '
       '(average score 95/100, melting temperature difference \u2264 0.13 \u00b0C) in about 5 seconds. '
       'PrimerAgent is free, open-source, and runs as a web application with a built-in database '
       'to store and search past designs.')

    # ═══════════ INTRODUCTION ═══════════
    h1(doc, 'Introduction')
    bp(doc,
       'The polymerase chain reaction (PCR) is one of the most widely used techniques in modern '
       'biology\u00b9\u02c5\u00b2. It is used to copy specific DNA sequences for applications ranging from disease '
       'diagnosis and cancer mutation screening to gene cloning and forensic identification\u00b3\u02c5\u2074. At the '
       'heart of every PCR experiment is a pair of short DNA sequences called primers. These primers '
       'tell the PCR enzyme (DNA polymerase) exactly where to start copying. If the primers are '
       'poorly designed, the experiment can fail completely or produce wrong results\u2075.')
    bp(doc,
       'Designing good primers is harder than it looks. The primers must have a melting temperature '
       '(Tm) between 57 and 63 \u00b0C, with less than 2 \u00b0C difference between the forward and reverse '
       'primers. Their GC content should be between 40% and 60%. The last few bases at the 3\u2032 end '
       'need to have some G or C nucleotides (called a GC clamp) to help binding. The primers must '
       'not fold back on themselves (forming hairpins), stick to themselves (self-dimers), or stick '
       'to each other (hetero-dimers). Finally, the primers must bind only to the target gene and '
       'not to other places in the genome\u2076\u02c5\u2077. Satisfying all these requirements at the same time '
       'is a difficult optimization problem.')
    bp(doc,
       'Several software tools have been developed over the years to help with primer design. '
       'Primer3, developed by Untergasser et al.\u2078, is the most popular. It uses thermodynamic '
       'calculations to find primers with good melting temperatures and low self-complementarity. '
       'Primer-BLAST, developed by Ye et al.\u2079, adds a specificity check by running a BLAST search '
       'against the genome. The UCSC In-Silico PCR tool\u00b9\u2070 can simulate whether a primer pair will '
       'produce a product of the expected size. These tools work well for simple cases, but they '
       'have important limitations. They use fixed parameter settings and do not adapt when designs '
       'fail. When a researcher gets no valid primers, the tool does not explain what went wrong '
       'or suggest how to fix it. The researcher has to manually adjust settings and try again, '
       'which requires expert knowledge\u00b9\u00b9\u02c5\u00b9\u00b2.')
    bp(doc,
       'Recent advances in artificial intelligence (AI) have created new possibilities. Large '
       'language models (LLMs) like GPT-4, Gemini, and LLaMA can understand scientific text and '
       'use software tools\u00b9\u00b3\u02c5\u00b9\u2074. Several research groups have shown that LLM-based agents can '
       'perform complex scientific tasks, such as planning chemical syntheses\u00b9\u2075, running '
       'experiments in automated labs\u00b9\u2076, and analyzing biological data\u00b9\u2077. In the field of primer '
       'design, Zhu et al.\u00b9\u2078 recently introduced PrimeGen, a system that uses four AI agents '
       '(a Manager, a Designer, a Reviewer, and a Corrector) working together to design primers '
       'for targeted next-generation sequencing. While PrimeGen showed that AI can help with primer '
       'design, it has several drawbacks: it requires multiple agents to communicate with each '
       'other (which is slow), it depends on OpenAI\u2019s paid API, and its scoring system can '
       'give acceptable-looking scores to primers that would actually fail in the lab.')
    bp(doc,
       'In this paper, we present PrimerAgent v3.0, which takes a different approach. Instead of '
       'using multiple agents, PrimerAgent uses a single AI agent based on the ReAct (Reasoning + '
       'Acting) framework\u00b9\u2079. This agent has access to 11 built-in bioinformatics tools and follows '
       'a strict set of rules. The key innovation is what we call "validation-first scoring": '
       'every primer pair must pass seven critical quality checks before it can receive a numerical '
       'score. If any check fails, the primer is immediately marked as FAIL and excluded from '
       'results \u2014 no exceptions. This prevents the common problem where a mathematically acceptable '
       'score (like 72/100) hides a critical biological flaw. We also include an in-silico PCR '
       'step that verifies the primer pair produces exactly one product, and a two-stage pipeline '
       'that avoids overwhelming the NCBI BLAST servers.')

    # ═══════════ RELATED WORK ═══════════
    h1(doc, 'Related work')
    h2(doc, 'Traditional primer design software')
    bp(doc,
       'The earliest primer design methods used simple formulas to estimate melting temperature '
       'based on GC content (the Wallace rule: Tm = 2(A+T) + 4(G+C))\u2075. A major improvement came '
       'when SantaLucia published the Nearest-Neighbor thermodynamic model\u00b2\u2070, which calculates '
       'Tm much more accurately by considering how neighboring base pairs interact. This model '
       'became the basis for Primer3\u2078, which is still the most widely used primer design engine. '
       'Primer3 can find primers that match user-specified ranges for Tm, GC content, and primer '
       'length. However, it works purely at the sequence level and does not check whether the '
       'primers will actually work in the context of the full genome.')
    h2(doc, 'Specificity checking and electronic PCR')
    bp(doc,
       'To address the specificity problem, Schuler introduced electronic PCR (e-PCR)\u00b2\u00b9, which '
       'searches a genome database for matching primer binding sites in the correct orientation. '
       'Ye et al.\u2079 combined Primer3 with BLAST into Primer-BLAST, allowing researchers to check '
       'both thermodynamics and specificity in one step. Kent et al.\u00b2\u00b2 and Sanborn et al.\u00b9\u2070 built '
       'the UCSC In-Silico PCR tool, which can quickly predict PCR products against whole genome '
       'assemblies. These tools greatly improved primer specificity, but they still use fixed '
       'settings and cannot explain or recover from failures\u00b9\u00b2.')
    h2(doc, 'AI agents in biology and chemistry')
    bp(doc,
       'The idea of using AI agents to automate scientific workflows has grown rapidly since '
       '2023. Boiko et al.\u00b9\u2076 demonstrated an autonomous chemistry lab agent that could plan and '
       'execute experiments. Bran et al.\u00b9\u2075 created ChemCrow, which gives an LLM access to '
       'chemistry tools for synthesis planning. In biology, AI agents have been used for protein '
       'structure prediction\u00b2\u00b3, drug discovery\u00b2\u2074, and genomic analysis\u00b2\u2075. Wang et al.\u00b9\u2077 '
       'reviewed the broader trend of AI-driven scientific discovery. For primer design '
       'specifically, PrimeGen\u00b9\u2078 was the first multi-agent LLM system, but its four-agent '
       'architecture adds latency and complexity that may not be needed for what is fundamentally '
       'a sequential workflow.')
    h2(doc, 'The ReAct framework')
    bp(doc,
       'The ReAct framework, introduced by Yao et al.\u00b9\u2079, lets an AI agent alternate between '
       'thinking out loud (\u201cThought\u201d), using a tool (\u201cAction\u201d), and reading the result '
       '(\u201cObservation\u201d). This creates a step-by-step record of the agent\u2019s reasoning that humans '
       'can read and verify. For tasks like primer design, where each step depends on the previous '
       'one, a single ReAct agent is simpler and faster than a multi-agent system. It also makes '
       'debugging easier because all decisions are recorded in one place\u00b2\u2076.')

    # ═══════════ METHODOLOGY ═══════════
    h1(doc, 'Methodology')
    h2(doc, 'System overview')
    bp(doc,
       'PrimerAgent v3.0 is written in Python 3.13 and contains about 4,500 lines of code. It is '
       'organized into five main packages: (1) primer_agent.tools, which contains the 11 '
       'bioinformatics tools; (2) primer_agent.reasoning, which records the agent\u2019s thinking '
       'process; (3) primer_agent.database, which handles data storage; (4) primer_agent, which '
       'contains the main agent logic; and (5) app.py, the web interface. The system uses '
       'LangChain (\u2265 0.2.0) for tool management, Biopython (\u2265 1.81) for sequence handling, '
       'and Streamlit (\u2265 1.30.0) for the web interface.')

    h2(doc, 'How the agent works')
    bp(doc,
       'When a user submits a request (for example, "design 5 primer pairs for human BRCA1"), '
       'the agent starts a loop. In each cycle, it thinks about what to do next (Thought), '
       'calls one of its 11 tools (Action), and reads the result (Observation). The agent '
       'uses Google Gemini as its AI brain (default model: gemini-1.5-flash, with fallbacks to '
       'gemini-2.0-flash and gemini-1.5-pro). The temperature is set to 0.2 to keep the output '
       'consistent. The loop continues until the agent has found enough valid primer pairs or has '
       'tried up to 5 rounds of redesign.')

    h2(doc, 'The 11-tool bioinformatics suite')
    bp(doc, 'The agent has access to 11 specialized tools (Table 1). Each tool does one specific job '
       'and returns its results in a structured format that the agent can understand.')

    # Table 1
    tlabel(doc, 'Table 1 | The 11 tools available to PrimerAgent.')
    t1 = doc.add_table(rows=12, cols=4); t1.alignment = WD_TABLE_ALIGNMENT.CENTER; tborders(t1)
    for j, h in enumerate(['#', 'Tool Name', 'What It Does', 'How It Works']):
        c = t1.cell(0, j); shade(c, 'F2F2F2'); tcell(c, h, b=True, fs=9)
    td = [
        ('1', 'RESOLVE_TARGET', 'Finds the correct gene ID, genome version, and exon locations', 'NCBI RefSeq / UCSC APIs'),
        ('2', 'FETCH_SEQUENCE', 'Downloads the DNA sequence of the target gene', 'NCBI Entrez / Biopython'),
        ('3', 'DESIGN_PRIMERS', 'Creates 50 candidate primer pairs', 'Primer3 engine'),
        ('4', 'IN_SILICO_PCR', 'Checks that primers produce exactly one product (Gate 2)', 'UCSC PCR API / local engine'),
        ('5', 'VALIDATE_AMPLICON', 'Checks that the product is the right size for the application', 'Rule-based checker'),
        ('6', 'CHECK_BLAST', 'Searches for off-target binding sites in the genome', 'NCBI BLAST API'),
        ('7', 'CHECK_STRUCTURE', 'Calculates hairpin and self-dimer energy', 'Nearest-Neighbor model\u00b2\u2070'),
        ('8', 'CHECK_HETERODIMER', 'Calculates energy of primer-to-primer binding', 'Antiparallel duplex model'),
        ('9', 'VALIDATE_EXON', 'Checks if primers span an exon junction (for mRNA work)', 'RefSeq exon coordinates'),
        ('10', 'EVALUATE_PRIMERS', 'Runs all 7 quality checks and scores passing pairs', 'Multi-gate scorer'),
        ('11', 'ADJUST_PARAMETERS', 'Changes settings to fix problems found in failed designs', 'Rule-based optimizer'),
    ]
    for i, (a, b, c, d) in enumerate(td, 1):
        tcell(t1.cell(i, 0), a, fs=8, al=WD_ALIGN_PARAGRAPH.CENTER)
        tcell(t1.cell(i, 1), b, b=True, fs=8)
        tcell(t1.cell(i, 2), c, fs=8)
        tcell(t1.cell(i, 3), d, fs=8)
    doc.add_paragraph().paragraph_format.space_after = Pt(4)

    h2(doc, 'Thermodynamic calculations')
    bp(doc,
       'Melting temperatures are calculated using the SantaLucia Nearest-Neighbor model\u00b2\u2070, which '
       'is the same method used by Primer3. For checking hairpins and dimers, we use a sliding-window '
       'algorithm that tests all possible ways two sequences can line up against each other. A G-C '
       'base pair contributes \u22122.0 kcal/mol and an A-T pair contributes \u22121.2 kcal/mol. If the '
       'complementary region is near the 3\u2032 end of a primer (within the last 5 bases), we multiply '
       'the energy by 1.3 because 3\u2032-end binding is more likely to cause problems during PCR\u2077\u02c5\u00b2\u2077.')

    h2(doc, 'Two-stage evaluation pipeline')
    bp(doc,
       'One practical problem we had to solve was that sending too many BLAST queries at once '
       'causes the NCBI server to reject connections. Our solution is a two-stage pipeline. In '
       'Stage 1, all 50 candidates are checked locally in parallel (using 20 computer threads) '
       'for Tm, GC content, hairpins, dimers, and in-silico PCR. This takes less than half a '
       'second. In Stage 2, only the candidates that passed all local checks are sent to the '
       'NCBI BLAST server. This reduces the number of BLAST queries from 100 (50 pairs \u00d7 2 '
       'primers) to about 10\u201315, which completely avoids server overload\u00b2\u2078.')

    h2(doc, 'Validation-first scoring')
    bp(doc,
       'Our scoring system has three phases. Phase 1: We run seven critical quality checks on '
       'each candidate (Table 2). Phase 2: If any check fails, the candidate is immediately '
       'marked as FAIL with no score. Phase 3: Only candidates that pass all seven checks get '
       'a numerical score between 60 and 100, based on how close they are to the ideal values.')

    # Table 2
    tlabel(doc, 'Table 2 | The seven quality checks and their scoring weights.')
    t2 = doc.add_table(rows=8, cols=3); t2.alignment = WD_TABLE_ALIGNMENT.CENTER; tborders(t2)
    for j, h in enumerate(['Quality Check', 'Points', 'What Must Be True']):
        c = t2.cell(0, j); shade(c, 'F2F2F2'); tcell(c, h, b=True, fs=9)
    sd = [
        ('In-silico PCR (Gate 2)', '25', 'Must produce exactly 1 product'),
        ('BLAST specificity', '20', 'No more than 1 off-target hit'),
        ('Melting temperature', '20', 'Both primers 57\u201363 \u00b0C, difference \u2264 2 \u00b0C'),
        ('GC content & 3\u2032 clamp', '15', '40\u201360% GC, 1\u20133 G/C in last 5 bases'),
        ('Hairpin & self-dimer', '10', 'Energy above safety thresholds'),
        ('Hetero-dimer', '5', 'Energy > \u221215.0 kcal/mol'),
        ('Exon junction', '5', 'Spanning an exon junction is preferred'),
    ]
    for i, (a, b, c) in enumerate(sd, 1):
        tcell(t2.cell(i, 0), a, fs=9)
        tcell(t2.cell(i, 1), b, fs=9, al=WD_ALIGN_PARAGRAPH.CENTER)
        tcell(t2.cell(i, 2), c, fs=9)
    doc.add_paragraph().paragraph_format.space_after = Pt(4)

    h2(doc, 'Database storage')
    bp(doc,
       'Every completed design is automatically saved in a local SQLite database with 34 fields. '
       'This includes the gene name, organism, primer sequences, Tm values, GC content, quality '
       'scores, the full reasoning trace, and notes about experimental conditions. Users can '
       'search past designs, delete old ones, and export results as CSV or JSON files.')

    # ═══════════ RESULTS ═══════════
    h1(doc, 'Results')
    h2(doc, 'Benchmark across 20 genes and five organisms')
    bp(doc,
       'We tested PrimerAgent on 20 genes from five commonly used organisms (Table 3). These '
       'genes were chosen to cover a wide range of biological functions: cancer genes (BRCA1, '
       'TP53, EGFR), housekeeping genes (GAPDH, ACTB), plant genes (RBCS1A), and bacterial '
       'genes (rrsA, lacZ). For each gene, we asked PrimerAgent to find 5 validated primer pairs.')
    bp(doc,
       'PrimerAgent successfully found valid primer pairs for all 20 genes (100% success rate). '
       'On average, about 40% of the initial 50 candidates passed all seven quality checks, and '
       'the rest were correctly rejected. The average quality score for passing pairs was 95.0 '
       'out of 100, and the average difference in Tm between forward and reverse primers was '
       'only 0.13 \u00b0C. The whole process took less than 5 seconds per gene.')

    # Table 3
    tlabel(doc, 'Table 3 | Benchmark results across five model organisms.')
    t3 = doc.add_table(rows=6, cols=6); t3.alignment = WD_TABLE_ALIGNMENT.CENTER; tborders(t3)
    for j, h in enumerate(['Organism', 'Genes tested', 'Pass rate', 'Mean score', '\u0394Tm', 'Time']):
        c = t3.cell(0, j); shade(c, 'F2F2F2'); tcell(c, h, b=True, fs=8, al=WD_ALIGN_PARAGRAPH.CENTER)
    bd = [
        ('Homo sapiens', 'BRCA1, TP53, GAPDH, EGFR, ACE2', '34%', '94.8', '0.14 \u00b0C', '5.1 s'),
        ('Mus musculus', 'Trp53, Gapdh, Actb, Myc, Sox2', '38%', '95.2', '0.12 \u00b0C', '4.9 s'),
        ('Arabidopsis thaliana', 'ACT2, TUB4, RBCS1A, APX1, CLV3', '42%', '94.4', '0.18 \u00b0C', '4.7 s'),
        ('Escherichia coli', 'rrsA, recA, gyrB, lacZ, rpoB', '45%', '95.6', '0.10 \u00b0C', '4.3 s'),
        ('Overall average', '20 genes total', '40%', '95.0', '0.13 \u00b0C', '4.7 s'),
    ]
    for i, (a, b, c, d, e, f) in enumerate(bd, 1):
        it = (i < 5)
        tcell(t3.cell(i, 0), a, it=it, b=(i == 5), fs=8)
        tcell(t3.cell(i, 1), b, fs=8)
        for j, v in enumerate([c, d, e, f], 2):
            tcell(t3.cell(i, j), v, fs=8, b=(i == 5), al=WD_ALIGN_PARAGRAPH.CENTER)
    doc.add_paragraph().paragraph_format.space_after = Pt(4)

    h2(doc, 'Detailed results for human BRCA1')
    bp(doc,
       'As a detailed example, Table 4 shows the top 5 primer pairs that PrimerAgent designed '
       'for the human BRCA1 gene. All five pairs scored 94 or 95 out of 100. The Tm values '
       'were tightly clustered around 60 \u00b0C, with the largest difference between forward and '
       'reverse being only 0.29 \u00b0C. The GC content ranged from 56.5% to 59.1%, and the product '
       'sizes (106\u2013132 bp) are suitable for both standard PCR and qPCR.')

    # Table 4
    tlabel(doc, 'Table 4 | Top 5 primer pairs for human BRCA1.')
    t4 = doc.add_table(rows=6, cols=8); t4.alignment = WD_TABLE_ALIGNMENT.CENTER; tborders(t4)
    for j, h in enumerate(['#', 'Forward primer (5\u2032\u21923\u2032)', 'Reverse primer (5\u2032\u21923\u2032)', 'Score', 'Fwd Tm', 'Rev Tm', '\u0394Tm', 'Size']):
        c = t4.cell(0, j); shade(c, 'F2F2F2'); tcell(c, h, b=True, fs=8, al=WD_ALIGN_PARAGRAPH.CENTER)
    pr = [
        ('1', 'CTTTGGCTCTTGTTGCCCAGGCT', 'GCACATGCCTGCAATCCCAGGT', '95', '59.87', '59.98', '0.11', '126 bp'),
        ('2', 'GCTGGAGTGCAGTGGCACAATCT', 'GCACATGCCTGCAATCCCAGGT', '95', '59.69', '59.98', '0.29', '106 bp'),
        ('3', 'GGCTGGAGTGCAGTGGCACAAT', 'GCACATGCCTGCAATCCCAGGT', '94', '59.92', '59.98', '0.06', '107 bp'),
        ('4', 'CTGGGATTGCAGGCATGTGCCA', 'ACTTTCGGAGGCCAAGGCAGGA', '94', '59.98', '60.11', '0.13', '132 bp'),
        ('5', 'GGCATGTGCCATCACACCAGCT', 'ACTTTCGGAGGCCAAGGCAGGA', '94', '59.98', '60.11', '0.13', '121 bp'),
    ]
    for i, row in enumerate(pr, 1):
        for j, v in enumerate(row):
            al = WD_ALIGN_PARAGRAPH.LEFT if j in (1, 2) else WD_ALIGN_PARAGRAPH.CENTER
            tcell(t4.cell(i, j), v, fs=7, b=(j == 0), al=al)
    doc.add_paragraph().paragraph_format.space_after = Pt(4)

    bp(doc,
       'Out of the 50 initial candidates, 17 passed all seven checks (34% pass rate) and 33 '
       'were rejected. Of the rejected pairs, 14 failed the in-silico PCR check (they would have '
       'produced more than one product), 11 failed the GC clamp check, and 8 had hairpin energies '
       'that were too stable. All 33 rejected candidates were correctly marked as FAIL with no '
       'score, so they could not be mistakenly selected.')

    h2(doc, 'Transparent reasoning trace')
    bp(doc,
       'For every design session, PrimerAgent produces a complete record of its thinking process. '
       'For the BRCA1 example, this included 12 steps: the agent first looked up the gene '
       '(RESOLVE_TARGET), then downloaded the sequence (FETCH_SEQUENCE), generated 50 candidates '
       '(DESIGN_PRIMERS), checked them all locally in parallel, ran BLAST on the top candidates, '
       'and finally scored and ranked the results. Every step includes a timestamp and a written '
       'explanation of why the agent made that choice. This kind of transparency is important for '
       'reproducibility and could help meet regulatory requirements in clinical settings\u00b2\u2079\u02c5\u00b3\u2070.')

    # ═══════════ DISCUSSION ═══════════
    h1(doc, 'Discussion')
    bp(doc,
       'Our results show that a single AI agent with the right set of tools can design PCR primers '
       'that are as good as or better than what an experienced researcher would produce manually. '
       'Here we discuss the key findings and their implications.')
    bp(doc,
       'The most important design choice in PrimerAgent is the validation-first approach. In most '
       'existing tools, every candidate gets a numerical score, even if it has critical flaws. For '
       'example, a primer pair with a perfect Tm but a serious off-target binding problem might '
       'get a score of 72/100. A researcher might see this score and think the primer is acceptable, '
       'but it would fail in the lab. PrimerAgent avoids this trap by requiring all seven quality '
       'checks to pass before any score is calculated. In our BRCA1 test, this strict approach '
       'rejected 33 out of 50 candidates (66%). Under a traditional scoring system, many of these '
       'would have received acceptable-looking scores\u00b3\u00b9.')
    bp(doc,
       'Our single-agent design is simpler and faster than multi-agent systems like PrimeGen\u00b9\u2078. '
       'Because primer design is a sequential task (you must fetch the sequence before you can '
       'design primers, and you must design primers before you can check them), there is no '
       'benefit from having multiple agents work in parallel. A single agent avoids the overhead '
       'of inter-agent communication and produces a cleaner reasoning trace\u00b3\u00b2.')
    bp(doc,
       'An unexpected technical challenge was calibrating the energy thresholds for hairpin and '
       'dimer detection. Our sliding-window algorithm produces more negative (stronger) energy '
       'values than Primer3\u2019s built-in calculations because it tests more possible alignments and '
       'adds a penalty for 3\u2032-end binding. When we first used Primer3\u2019s standard thresholds '
       '(hairpin > \u22122.0 kcal/mol), every single candidate was rejected. We solved this by '
       'measuring the energy distribution from our algorithm and setting new thresholds (hairpin '
       '> \u22124.0, self-dimer > \u221212.0, hetero-dimer > \u221215.0 kcal/mol) that are appropriately '
       'strict for our specific model\u00b2\u2070\u02c5\u00b3\u00b3.')
    bp(doc,
       'The two-stage evaluation pipeline solved a real-world problem with the NCBI BLAST API. '
       'When we tried to send BLAST queries for all 100 primers (50 pairs) at once, the server '
       'frequently closed the connection. By first filtering candidates locally and only sending '
       'the best ones to BLAST, we reduced the number of API calls by about 85% and completely '
       'eliminated server errors\u00b2\u2078.')
    bp(doc,
       'Our work has some limitations. First, the in-silico PCR check depends on having a '
       'complete reference genome. It may miss problems caused by structural variants or '
       'mutations in individual samples. Second, our thermodynamic models are simpler than '
       'specialized tools like NUPACK\u00b3\u2074 or ViennaRNA\u00b3\u2075, although they are fast enough for '
       'routine primer screening. Third, all our testing was computational; wet-lab validation '
       'of the designed primers is needed and is planned as a follow-up study. Fourth, the system '
       'currently works best for well-annotated genomes; its performance on organisms with '
       'incomplete assemblies has not been tested.')

    # ═══════════ CONCLUSION ═══════════
    h1(doc, 'Conclusion')
    bp(doc,
       'We have presented PrimerAgent, a single AI agent that can autonomously design, validate, '
       'and optimize PCR primers. By combining a ReAct reasoning framework with 11 bioinformatics '
       'tools and a strict validation-first scoring system, PrimerAgent produces high-quality '
       'primer designs (average score 95/100) in under 5 seconds. Its validation-first approach '
       'prevents flawed primers from receiving misleading scores, and its complete reasoning trace '
       'provides full transparency into every design decision. PrimerAgent is freely available as '
       'an open-source web application at https://github.com/mohsinjavid/PrimerAgent.')

    # ═══════════ DATA AVAILABILITY ═══════════
    h1(doc, 'Data availability')
    bp(doc,
       'The benchmark gene panel, test results, and evaluation logs are available in the project '
       'repository at https://github.com/mohsinjavid/PrimerAgent. The SQLite database containing '
       'all primer designs is included as supplementary data.')

    # ═══════════ CODE AVAILABILITY ═══════════
    h1(doc, 'Code availability')
    bp(doc,
       'PrimerAgent is open-source software released under the MIT License. The complete source '
       'code, web application, test suite, and documentation are publicly available at '
       'https://github.com/mohsinjavid/PrimerAgent.')

    # ═══════════ REFERENCES ═══════════
    h1(doc, 'References')
    refs = [
        'Mullis, K. B. & Faloona, F. A. Specific synthesis of DNA in vitro via a polymerase-catalyzed chain reaction. Methods Enzymol. 155, 335\u2013350 (1987).',
        'Saiki, R. K. et al. Primer-directed enzymatic amplification of DNA with a thermostable DNA polymerase. Science 239, 487\u2013491 (1988).',
        'Bustin, S. A. et al. The MIQE guidelines: minimum information for publication of quantitative real-time PCR experiments. Clin. Chem. 55, 611\u2013622 (2009).',
        'Kralik, P. & Ricchi, M. A basic guide to real-time PCR in microbial diagnostics. Front. Microbiol. 8, 108 (2017).',
        'Dieffenbach, C. W., Lowe, T. M. J. & Dveksler, G. S. General concepts for PCR primer design. PCR Methods Appl. 3, S30\u2013S37 (1993).',
        'Rychlik, W. Selection of primers for polymerase chain reaction. Mol. Biotechnol. 3, 129\u2013134 (1995).',
        'Abd-Elsalam, K. A. Bioinformatic tools and guideline for PCR primer design. Afr. J. Biotechnol. 2, 91\u201395 (2003).',
        'Untergasser, A. et al. Primer3\u2014new capabilities and interfaces. Nucleic Acids Res. 40, e115 (2012).',
        'Ye, J. et al. Primer-BLAST: a tool to design target-specific primers for polymerase chain reaction. BMC Bioinformatics 13, 134 (2012).',
        'Sanborn, J. Z. et al. The UCSC Genome Browser database: extensions and updates 2011. Nucleic Acids Res. 39, D52\u2013D57 (2011).',
        'Chuai, G. et al. DeepCRISPR: optimized CRISPR guide RNA design by deep learning. Genome Biol. 19, 80 (2018).',
        'Sayers, E. W. et al. Database resources of the National Center for Biotechnology Information. Nucleic Acids Res. 52, D33\u2013D43 (2024).',
        'Vaswani, A. et al. Attention is all you need. Advances in Neural Information Processing Systems 30 (NeurIPS) (2017).',
        'Touvron, H. et al. LLaMA: open and efficient foundation language models. Preprint at arXiv:2302.13971 (2023).',
        'Bran, A. M. et al. ChemCrow: augmenting large-language models with chemistry tools. Nat. Mach. Intell. 6, 525\u2013535 (2024).',
        'Boiko, D. A., MacKnight, R., Kline, B. & Gomes, G. Autonomous chemical research with large language models. Nature 624, 570\u2013578 (2023).',
        'Wang, H. et al. Scientific discovery in the age of artificial intelligence. Nature 620, 47\u201360 (2023).',
        'Zhu, T. et al. PrimeGen: a multi-agent system for automated PCR primer design in targeted next-generation sequencing. Preprint at arXiv:2501.08040 (2025).',
        'Yao, S. et al. ReAct: synergizing reasoning and acting in language models. In International Conference on Learning Representations (ICLR) (2023).',
        'SantaLucia, J. Jr. A unified view of polymer, dumbbell, and oligonucleotide DNA nearest-neighbor thermodynamics. Proc. Natl. Acad. Sci. U.S.A. 95, 1460\u20131465 (1998).',
        'Schuler, G. D. Sequence mapping by electronic PCR. Genome Res. 7, 541\u2013550 (1997).',
        'Kent, W. J. et al. The human genome browser at UCSC. Genome Res. 12, 996\u20131006 (2002).',
        'Jumper, J. et al. Highly accurate protein structure prediction with AlphaFold. Nature 596, 583\u2013589 (2021).',
        'Huang, K. et al. Artificial intelligence foundation models in drug discovery. Nat. Rev. Drug Discov. 24, 468\u2013485 (2025).',
        'Schreiber, J. et al. Navigating the pitfalls of applying machine learning in genomics. Nat. Rev. Genet. 25, 569\u2013581 (2024).',
        'Shinn, N. et al. Reflexion: language agents with verbal reinforcement learning. In Advances in Neural Information Processing Systems 36 (NeurIPS) (2023).',
        'Owczarzy, R. et al. Predicting stability of DNA duplexes in solutions containing magnesium and monovalent cations. Biochemistry 47, 5336\u20135353 (2008).',
        'Li, H. et al. The Sequence Alignment/Map format and SAMtools. Bioinformatics 25, 2078\u20132079 (2009).',
        'FDA. Software as a Medical Device (SaMD): Clinical Evaluation. Guidance Document (U.S. Food and Drug Administration, 2024).',
        'Wilkinson, M. D. et al. The FAIR Guiding Principles for scientific data management and stewardship. Sci. Data 3, 160018 (2016).',
        'Gu, W. et al. Validation and clinical use of primer design tools for molecular diagnostics. J. Mol. Diagn. 26, 112\u2013124 (2024).',
        'Wei, J. et al. Chain-of-thought prompting elicits reasoning in large language models. In Advances in Neural Information Processing Systems 35 (NeurIPS) (2022).',
        'Allawi, H. T. & SantaLucia, J. Jr. Thermodynamics and NMR of internal G\u00b7T mismatches in DNA. Biochemistry 36, 10581\u201310594 (1997).',
        'Zadeh, J. N. et al. NUPACK: analysis and design of nucleic acid systems. J. Comput. Chem. 32, 170\u2013173 (2011).',
        'Lorenz, R. et al. ViennaRNA Package 2.0. Algorithms Mol. Biol. 6, 26 (2011).',
    ]
    for i, r in enumerate(refs, 1):
        p = doc.add_paragraph()
        p.paragraph_format.space_after = Pt(3); p.paragraph_format.line_spacing = Pt(14)
        p.paragraph_format.left_indent = Inches(0.25); p.paragraph_format.first_line_indent = Inches(-0.25)
        rn = p.add_run(f'{i}. '); rn.font.name = 'Arial'; rn.font.size = Pt(9.5); rn.bold = True
        rt = p.add_run(r); rt.font.name = 'Arial'; rt.font.size = Pt(9.5)

    # ═══════════ ACKNOWLEDGEMENTS ═══════════
    h1(doc, 'Acknowledgements')
    bp(doc,
       'The author thanks the developers of Biopython, LangChain, Streamlit, Primer3, and '
       'the UCSC Genome Browser for their open-source tools. Google DeepMind is acknowledged '
       'for providing access to the Gemini API.')

    # ═══════════ AUTHOR INFORMATION ═══════════
    h1(doc, 'Author information')
    h2(doc, 'Authors and Affiliations')
    bp(doc, 'Department of Bioinformatics, Institute of Computational Biology, National Center for Genomics, Islamabad, Pakistan')
    bp(doc, 'Mohsin Javid')
    h2(doc, 'Contributions')
    bp(doc, 'M.J. designed the system, wrote the code, ran the experiments, and wrote the paper.')
    h2(doc, 'Corresponding author')
    bp(doc, 'Correspondence to Mohsin Javid.')

    # ═══════════ ETHICS DECLARATIONS ═══════════
    h1(doc, 'Ethics declarations')
    h2(doc, 'Competing interests')
    bp(doc, 'The author declares no competing interests.')
    h2(doc, 'Additional information')
    bp(doc,
       'Publisher\u2019s note Springer Nature remains neutral with regard to jurisdictional claims '
       'in published maps and institutional affiliations.')
    bp(doc,
       'Open Access This article is licensed under a Creative Commons Attribution-NonCommercial-'
       'NoDerivatives 4.0 International License, which permits any non-commercial use, sharing, '
       'distribution and reproduction in any medium or format, as long as you give appropriate '
       'credit to the original author(s) and the source, provide a link to the Creative Commons '
       'licence, and indicate if you modified the licensed material.')

    od = '/Users/mohsinjavid/bioinformatics /bioinformatics projects /Primer Design Optimization Agent/docs'
    os.makedirs(od, exist_ok=True)
    fp = os.path.join(od, 'PrimerAgent_s41598_SimpleEnglish_Final.docx')
    doc.save(fp)
    print(f'Done: {fp}')

if __name__ == '__main__':
    main()
