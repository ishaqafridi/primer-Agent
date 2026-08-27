"""
PrimerAgent Benchmarking Framework

Provides reproducible benchmarking infrastructure evaluating design success rate,
execution time, thermodynamic accuracy, secondary structure propensity, and specificity
across 60 benchmark cases (20 genes × 3 application presets).
"""

from benchmarks.metrics import calculate_benchmark_metrics
from benchmarks.benchmark_runner import BenchmarkRunner
from benchmarks.analysis import generate_benchmark_report
