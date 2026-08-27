"""
PrimerAgent Benchmark Runner

Executes the automated benchmarking protocol across 60 test cases (20 genes × 3 application presets)
and records detailed performance metrics.

Usage:
    python -m benchmarks.benchmark_runner [--fast-mode] [--output benchmark_results.json]
"""

import os
import sys
import json
import time
import argparse
import logging
from typing import Dict, Any, List

from primer_agent.react_agent import PrimerReActAgent
from benchmarks.metrics import calculate_benchmark_metrics

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


class BenchmarkRunner:
    """Orchestrates reproducible benchmarking suite for PrimerAgent."""

    def __init__(self, gene_dataset_path: str = None, fast_mode: bool = True):
        """
        Initialize the runner.
        
        Args:
            gene_dataset_path: Path to benchmark_genes.json file.
            fast_mode: If True, skip live NCBI BLAST queries to speed up benchmark.
        """
        if gene_dataset_path is None:
            gene_dataset_path = os.path.join(
                os.path.dirname(__file__), "benchmark_genes.json"
            )

        with open(gene_dataset_path, "r") as f:
            self.genes = json.load(f)

        self.fast_mode = fast_mode
        self.presets = ["Standard PCR", "qPCR", "Sanger Sequencing"]
        self.agent = PrimerReActAgent()

    def run_all(self) -> Dict[str, Any]:
        """
        Execute all 60 benchmark test cases (20 genes × 3 presets).
        
        Returns:
            Dict containing raw case results and summary metrics.
        """
        logger.info(f"Starting Benchmark Suite: {len(self.genes)} genes × {len(self.presets)} presets = {len(self.genes) * len(self.presets)} test cases")
        start_suite_time = time.time()

        case_results = []
        case_idx = 0

        for gene_entry in self.genes:
            gene_symbol = gene_entry["gene_symbol"]
            organism = gene_entry["organism"]

            for preset in self.presets:
                case_idx += 1
                logger.info(f"[{case_idx}/60] Running: {gene_symbol} ({organism}) — Preset: {preset}")

                t0 = time.time()
                try:
                    res = self.agent.run(
                        gene_name=gene_symbol,
                        organism=organism,
                        application=preset,
                        skip_blast=self.fast_mode,
                    )
                    t_elapsed = time.time() - t0

                    case_results.append({
                        "case_id": case_idx,
                        "gene_symbol": gene_symbol,
                        "organism": organism,
                        "category": gene_entry.get("category", "General"),
                        "preset": preset,
                        "execution_time": round(t_elapsed, 2),
                        "best_score": res.get("best_score", 0.0),
                        "design_passed": res.get("design_passed", False),
                        "iteration_count": res.get("state", {}).get("iteration_count", 1),
                        "validated_results": res.get("validated_results", []),
                        "status": "SUCCESS",
                    })
                except Exception as e:
                    t_elapsed = time.time() - t0
                    logger.error(f"Test case #{case_idx} failed: {e}")
                    case_results.append({
                        "case_id": case_idx,
                        "gene_symbol": gene_symbol,
                        "organism": organism,
                        "category": gene_entry.get("category", "General"),
                        "preset": preset,
                        "execution_time": round(t_elapsed, 2),
                        "best_score": 0.0,
                        "design_passed": False,
                        "iteration_count": 0,
                        "validated_results": [],
                        "status": f"ERROR: {str(e)}",
                    })

        total_suite_time = time.time() - start_suite_time
        summary_metrics = calculate_benchmark_metrics(case_results)
        summary_metrics["total_suite_runtime_sec"] = round(total_suite_time, 2)

        return {
            "summary_metrics": summary_metrics,
            "case_results": case_results,
        }


def main():
    parser = argparse.ArgumentParser(description="Run PrimerAgent Benchmark Suite")
    parser.add_argument("--fast-mode", action="store_true", default=True, help="Skip live web BLAST queries for speed")
    parser.add_argument("--output", type=str, default="benchmark_results.json", help="Output JSON path")
    args = parser.parse_args()

    runner = BenchmarkRunner(fast_mode=args.fast_mode)
    benchmark_data = runner.run_all()

    with open(args.output, "w") as f:
        json.dump(benchmark_data, f, indent=2)

    logger.info(f"Benchmark completed successfully! Saved to {args.output}")
    print("\n" + "="*60)
    print(" 📊 PRIMERAGENT BENCHMARK SUMMARY RESULTS")
    print("="*60)
    for k, v in benchmark_data["summary_metrics"].items():
        print(f" - {k:<30}: {v}")
    print("="*60)


if __name__ == "__main__":
    main()
