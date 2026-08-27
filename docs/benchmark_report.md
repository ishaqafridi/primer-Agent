# 📊 PrimerAgent v2.0 Benchmark Evaluation Report

**Generated on:** benchmark_report.md  
**Evaluation Scope:** 60 Benchmark Cases (20 Genes × 3 Presets)  

---

## Executive Summary

- **Design Success Rate**: 100.0%
- **Mean Quality Score**: 98.02 / 100
- **Mean Execution Time**: 6.01 seconds per design
- **Mean Tm Difference**: 0.07 °C
- **GC Content Compliance**: 100.0%
- **Secondary Structure Pass Rates**:
  - Hairpin MFE Pass: 100.0%
  - Self-Dimer MFE Pass: 78.33%
  - Hetero-Dimer MFE Pass: 95.0%

---


### Comparative Feature & Architecture Table

| Feature / Metric | PrimerAgent v2.0 | PrimeGen (2025) | Primer3 | NCBI Primer-BLAST | IDT PrimerQuest |
|------------------|------------------|-----------------|---------|-------------------|-----------------|
| **AI Paradigm** | Single-Agent ReAct | Multi-Agent Orchestrator | Algorithmic | Algorithmic | Web / Rule-based |
| **LLM Engine** | Google Gemini | GPT-4o | None | None | None |
| **Dynamic Tool Selection** | ✅ Yes (LLM-driven) | ❌ Pre-assigned | ❌ No | ❌ No | ❌ No |
| **Explainable Reasoning** | ✅ Full Trace | ❌ Implicit | ❌ None | ❌ None | ❌ None |
| **Thermodynamic MFE Audit** | ✅ Primer3 + ViennaRNA | ✅ Primer3 | ✅ Built-in | ❌ Partial | ✅ Built-in |
| **Specificity Verification** | ✅ Integrated BLAST | ✅ Integrated BLAST | ❌ Requires manual BLAST | ✅ Integrated BLAST | ❌ Manual |
| **Adaptive Self-Correction** | ✅ Biological Critic | ✅ Vision / Robotic | ❌ Manual retry | ❌ Manual retry | ❌ Manual retry |
| **Confidence Assessment** | ✅ LLM Biological | ❌ Not reported | ❌ None | ❌ None | ❌ None |
| **Built-in DB Persistence** | ✅ SQLite / Postgres | ❌ No DB | ❌ File export | ❌ None | ❌ Web session |
| **Target Application** | General PCR / qPCR | Amplicon Sequencing (tNGS) | General PCR | General PCR | General PCR / qPCR |


---

## Individual Benchmark Test Case Results

| Case ID | Gene | Organism | Application Preset | Quality Score | Execution Time (s) | Status |
|---------|------|----------|--------------------|---------------|----------------────|--------|
| 1 | BRCA1 | Homo sapiens | Standard PCR | 97/100 | 2.9s | SUCCESS |
| 2 | BRCA1 | Homo sapiens | qPCR | 97/100 | 3.13s | SUCCESS |
| 3 | BRCA1 | Homo sapiens | Sanger Sequencing | 100/100 | 3.29s | SUCCESS |
| 4 | TP53 | Homo sapiens | Standard PCR | 97/100 | 2.64s | SUCCESS |
| 5 | TP53 | Homo sapiens | qPCR | 97/100 | 2.69s | SUCCESS |
| 6 | TP53 | Homo sapiens | Sanger Sequencing | 100/100 | 2.92s | SUCCESS |
| 7 | GAPDH | Homo sapiens | Standard PCR | 95/100 | 3.96s | SUCCESS |
| 8 | GAPDH | Homo sapiens | qPCR | 100/100 | 2.93s | SUCCESS |
| 9 | GAPDH | Homo sapiens | Sanger Sequencing | 97/100 | 2.73s | SUCCESS |
| 10 | EGFR | Homo sapiens | Standard PCR | 100/100 | 2.86s | SUCCESS |
| 11 | EGFR | Homo sapiens | qPCR | 100/100 | 1.74s | SUCCESS |
| 12 | EGFR | Homo sapiens | Sanger Sequencing | 97/100 | 4.93s | SUCCESS |
| 13 | ACE2 | Homo sapiens | Standard PCR | 100/100 | 2.54s | SUCCESS |
| 14 | ACE2 | Homo sapiens | qPCR | 100/100 | 5.62s | SUCCESS |
| 15 | ACE2 | Homo sapiens | Sanger Sequencing | 100/100 | 3.15s | SUCCESS |
| 16 | Trp53 | Mus musculus | Standard PCR | 100/100 | 3.28s | SUCCESS |
| 17 | Trp53 | Mus musculus | qPCR | 100/100 | 3.74s | SUCCESS |
| 18 | Trp53 | Mus musculus | Sanger Sequencing | 100/100 | 3.36s | SUCCESS |
| 19 | Gapdh | Mus musculus | Standard PCR | 95/100 | 2.44s | SUCCESS |
| 20 | Gapdh | Mus musculus | qPCR | 100/100 | 5.08s | SUCCESS |
| 21 | Gapdh | Mus musculus | Sanger Sequencing | 100/100 | 5.07s | SUCCESS |
| 22 | Actb | Mus musculus | Standard PCR | 100/100 | 2.7s | SUCCESS |
| 23 | Actb | Mus musculus | qPCR | 100/100 | 3.75s | SUCCESS |
| 24 | Actb | Mus musculus | Sanger Sequencing | 100/100 | 4.98s | SUCCESS |
| 25 | Myc | Mus musculus | Standard PCR | 100/100 | 2.99s | SUCCESS |
| 26 | Myc | Mus musculus | qPCR | 90/100 | 2.7s | SUCCESS |
| 27 | Myc | Mus musculus | Sanger Sequencing | 100/100 | 5.05s | SUCCESS |
| 28 | Sox2 | Mus musculus | Standard PCR | 100/100 | 3.89s | SUCCESS |
| 29 | Sox2 | Mus musculus | qPCR | 97/100 | 3.23s | SUCCESS |
| 30 | Sox2 | Mus musculus | Sanger Sequencing | 100/100 | 4.38s | SUCCESS |
| 31 | ACT2 | Arabidopsis thaliana | Standard PCR | 92/100 | 13.49s | SUCCESS |
| 32 | ACT2 | Arabidopsis thaliana | qPCR | 95/100 | 10.13s | SUCCESS |
| 33 | ACT2 | Arabidopsis thaliana | Sanger Sequencing | 95/100 | 13.06s | SUCCESS |
| 34 | TUB4 | Arabidopsis thaliana | Standard PCR | 92/100 | 10.84s | SUCCESS |
| 35 | TUB4 | Arabidopsis thaliana | qPCR | 95/100 | 12.16s | SUCCESS |
| 36 | TUB4 | Arabidopsis thaliana | Sanger Sequencing | 95/100 | 11.61s | SUCCESS |
| 37 | RBCS1A | Arabidopsis thaliana | Standard PCR | 100/100 | 5.48s | SUCCESS |
| 38 | RBCS1A | Arabidopsis thaliana | qPCR | 100/100 | 5.2s | SUCCESS |
| 39 | RBCS1A | Arabidopsis thaliana | Sanger Sequencing | 100/100 | 3.62s | SUCCESS |
| 40 | APX1 | Arabidopsis thaliana | Standard PCR | 97/100 | 2.41s | SUCCESS |
| 41 | APX1 | Arabidopsis thaliana | qPCR | 100/100 | 2.19s | SUCCESS |
| 42 | APX1 | Arabidopsis thaliana | Sanger Sequencing | 100/100 | 2.72s | SUCCESS |
| 43 | CLV3 | Arabidopsis thaliana | Standard PCR | 95/100 | 35.65s | SUCCESS |
| 44 | CLV3 | Arabidopsis thaliana | qPCR | 95/100 | 46.01s | SUCCESS |
| 45 | CLV3 | Arabidopsis thaliana | Sanger Sequencing | 100/100 | 12.63s | SUCCESS |
| 46 | rrsA | Escherichia coli | Standard PCR | 100/100 | 11.46s | SUCCESS |
| 47 | rrsA | Escherichia coli | qPCR | 95/100 | 4.93s | SUCCESS |
| 48 | rrsA | Escherichia coli | Sanger Sequencing | 100/100 | 20.43s | SUCCESS |
| 49 | recA | Escherichia coli | Standard PCR | 95/100 | 2.86s | SUCCESS |
| 50 | recA | Escherichia coli | qPCR | 100/100 | 2.84s | SUCCESS |
| 51 | recA | Escherichia coli | Sanger Sequencing | 100/100 | 3.1s | SUCCESS |
| 52 | gyrB | Escherichia coli | Standard PCR | 95/100 | 2.71s | SUCCESS |
| 53 | gyrB | Escherichia coli | qPCR | 95/100 | 2.55s | SUCCESS |
| 54 | gyrB | Escherichia coli | Sanger Sequencing | 100/100 | 2.6s | SUCCESS |
| 55 | lacZ | Escherichia coli | Standard PCR | 100/100 | 2.85s | SUCCESS |
| 56 | lacZ | Escherichia coli | qPCR | 100/100 | 2.9s | SUCCESS |
| 57 | lacZ | Escherichia coli | Sanger Sequencing | 97/100 | 2.56s | SUCCESS |
| 58 | rpoB | Escherichia coli | Standard PCR | 97/100 | 2.19s | SUCCESS |
| 59 | rpoB | Escherichia coli | qPCR | 97/100 | 2.23s | SUCCESS |
| 60 | rpoB | Escherichia coli | Sanger Sequencing | 100/100 | 2.31s | SUCCESS |

---

> [!NOTE]
> Comparative metrics against external platforms represent architectural baseline features. All measured PrimerAgent metrics are generated reproducibly from the execution runner.
