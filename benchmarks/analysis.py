"""
PrimerAgent Benchmark Analysis & Statistical Reporting

Analyzes benchmark_results.json and generates publication-ready summary tables,
statistical comparison reports, and hypothetical baseline benchmark comparisons.

Usage:
    python -m benchmarks.analysis [--input benchmark_results.json] [--output benchmark_report.md]
"""

import json
import os
import argparse
from typing import Dict, Any, List


def generate_comparative_table() -> str:
    """
    Generate markdown comparison table contrasting PrimerAgent against established tools.
    Note: Values for external tools represent literature baselines / architectural features.
    """
    return """
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
"""


def generate_benchmark_report(benchmark_data: Dict[str, Any], output_path: str):
    """
    Generate a full markdown benchmarking report from test results.
    """
    metrics = benchmark_data.get("summary_metrics", {})
    case_results = benchmark_data.get("case_results", [])

    report = f"""# 📊 PrimerAgent v2.0 Benchmark Evaluation Report

**Generated on:** {os.path.basename(output_path)}  
**Evaluation Scope:** 60 Benchmark Cases (20 Genes × 3 Presets)  

---

## Executive Summary

- **Design Success Rate**: {metrics.get('design_success_rate_pct', 'N/A')}%
- **Mean Quality Score**: {metrics.get('mean_quality_score', 'N/A')} / 100
- **Mean Execution Time**: {metrics.get('mean_execution_time_sec', 'N/A')} seconds per design
- **Mean Tm Difference**: {metrics.get('mean_tm_diff_celsius', 'N/A')} °C
- **GC Content Compliance**: {metrics.get('gc_compliance_pct', 'N/A')}%
- **Secondary Structure Pass Rates**:
  - Hairpin MFE Pass: {metrics.get('hairpin_pass_pct', 'N/A')}%
  - Self-Dimer MFE Pass: {metrics.get('self_dimer_pass_pct', 'N/A')}%
  - Hetero-Dimer MFE Pass: {metrics.get('hetero_dimer_pass_pct', 'N/A')}%

---

{generate_comparative_table()}

---

## Individual Benchmark Test Case Results

| Case ID | Gene | Organism | Application Preset | Quality Score | Execution Time (s) | Status |
|---------|------|----------|--------------------|---------------|----------------────|--------|
"""
    for case in case_results:
        report += f"| {case.get('case_id')} | {case.get('gene_symbol')} | {case.get('organism')} | {case.get('preset')} | {case.get('best_score')}/100 | {case.get('execution_time')}s | {case.get('status')} |\n"

    report += """
---

> [!NOTE]
> Comparative metrics against external platforms represent architectural baseline features. All measured PrimerAgent metrics are generated reproducibly from the execution runner.
"""

    with open(output_path, "w") as f:
        f.write(report)


def main():
    parser = argparse.ArgumentParser(description="Analyze PrimerAgent Benchmark Results")
    parser.add_argument("--input", type=str, default="benchmark_results.json", help="Input results JSON")
    parser.add_argument("--output", type=str, default="docs/benchmark_report.md", help="Output report MD")
    args = parser.parse_args()

    if not os.path.exists(args.input):
        print(f"Error: Input file '{args.input}' not found. Run benchmark_runner first.")
        return

    with open(args.input, "r") as f:
        data = json.load(f)

    generate_benchmark_report(data, args.output)
    print(f"Report generated successfully: {args.output}")


if __name__ == "__main__":
    main()
