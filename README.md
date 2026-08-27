# 🧬 PrimerAgent v2.0 — ReAct-Based AI Agent for PCR Primer Design

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Google Gemini](https://img.shields.io/badge/LLM-Google%20Gemini-orange.svg)](https://ai.google.dev/)
[![Streamlit](https://img.shields.io/badge/UI-Streamlit-ff4b4b.svg)](https://streamlit.io/)

**PrimerAgent v2.0** is an autonomous, single-agent AI system powered by **Google Gemini** that designs, validates, and optimizes PCR primers through iterative biological reasoning. Operating on the **ReAct (Reasoning + Acting)** paradigm, PrimerAgent dynamically decides which bioinformatics tools to invoke at each step, producing fully explainable decision traces alongside publication-quality primer recommendations.

---

## 🌟 Key Features

- **Genuine ReAct Architecture**: Gemini autonomously reasons through problem state, selects tools, and evaluates outcomes using explicit `Thought → Action → Observation` cycles.
- **Single-Agent Simplicity**: Low-latency, containerizable single-agent design avoiding multi-agent orchestration overhead.
- **7 Integrated Bioinformatics Tools**:
  1. *NCBI Sequence Fetcher*: Sequence retrieval by gene symbol or accession ID.
  2. *Primer-BLAST Design Engine*: Sequence & thermodynamic candidate pair generation.
  3. *BLAST Off-Target Checker*: Specifcity verification across genome databases.
  4. *Secondary Structure Checker*: Hairpin and homodimer MFE prediction (Nearest-Neighbor / ViennaRNA).
  5. *Hetero-Dimer Checker*: Cross-primer thermodynamic stability audit.
  6. *Quality Evaluator*: Weighted multi-criteria scoring system (0–100 scale).
  7. *Parameter Adjuster (Critic)*: Targeted Primer-BLAST constraint optimization for failed designs.
- **Explainable Reasoning Traces**: Complete audit trail showing every biological decision made by the agent.
- **Biological Confidence Scoring**: LLM-enhanced confidence metrics explaining experimental suitability.
- **Integrated Primer Database**: Built-in SQLite database (with PostgreSQL schema) for design persistence and search.
- **Modern Streamlit Interface**: Real-time reasoning visualization, interactive metrics, and report downloads.

---

## 🏗️ System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                      PrimerAgent v2.0                          │
│              Single-Agent ReAct Architecture                    │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  User Request: "Design primers for BRCA1 in human for qPCR"     │
│       │                                                         │
│       ▼                                                         │
│  ┌──────────────────────────────────┐                          │
│  │     Google Gemini LLM Engine     │◄──── System Prompt       │
│  │   (Reasoning + Tool Selection)   │      (Biological Expert) │
│  └──────────┬───────────────────────┘                          │
│             │                                                   │
│             ▼                                                   │
│  ┌──────────────────────────────────┐                          │
│  │      ReAct Reasoning Loop        │                          │
│  │                                  │                          │
│  │  THOUGHT → ACTION → OBSERVATION  │                          │
│  │       ↑                  │       │                          │
│  │       └──────────────────┘       │                          │
│  │      (iterate until done)        │                          │
│  └──────────┬───────────────────────┘                          │
│             │                                                   │
│             ▼                                                   │
│  ┌──────────────────────────────────┐                          │
│  │         Tool Suite (7 Tools)      │                         │
│  ├──────────────────────────────────┤                          │
│  │ 1. NCBI Sequence Fetcher         │  Biopython / Entrez     │
│  │ 2. Primer-BLAST Design Engine    │  NCBI Primer-BLAST / NN │
│  │ 3. BLAST Off-Target Checker      │  NCBI BLAST API         │
│  │ 4. Secondary Structure Checker   │  NN / ViennaRNA         │
│  │ 5. Hetero-Dimer Checker          │  Nearest-Neighbor       │
│  │ 6. Quality Evaluator (0-100)     │  Multi-criteria scorer  │
│  │ 7. Parameter Adjuster (Critic)   │  Intelligent optimizer  │
│  └──────────────────────────────────┘                          │
│             │                                                   │
│             ▼                                                   │
│  ┌──────────────────────────────────┐                          │
│  │      Output Layer                │                          │
│  ├──────────────────────────────────┤                          │
│  │ • Validated primer pairs         │                          │
│  │ • Quality scores & QC audit      │                          │
│  │ • Confidence assessment          │                          │
│  │ • Full reasoning trace           │                          │
│  │ • Wet-lab recommendations        │                          │
│  │ • SQLite database storage        │                          │
│  └──────────────────────────────────┘                          │
└─────────────────────────────────────────────────────────────────┘
```

---

## ⚡ Quick Start

### Prerequisites

- Python 3.10+
- Google Gemini API key ([Get one free at Google AI Studio](https://ai.google.dev/))

### Installation

1. **Clone the repository**:
   ```bash
   git clone https://github.com/your-org/PrimerAgent.git
   cd PrimerAgent
   ```

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Set your API Key**:
   ```bash
   export GOOGLE_API_KEY="your-gemini-api-key"
   ```

4. **Launch the Streamlit Web UI**:
   ```bash
   streamlit run app.py
   ```

---

## 💻 Programmatic Usage

You can also use PrimerAgent directly in your Python code:

```python
from primer_agent.react_agent import PrimerReActAgent

# Initialize agent with Google Gemini
agent = PrimerReActAgent(
    api_key="your-google-api-key",
    model_name="gemini-1.5-flash"
)

# Run autonomous primer design
result = agent.run(
    gene_name="GAPDH",
    organism="Homo sapiens",
    application="qPCR",
    product_size_range=(100, 200),
    num_return=3,
    skip_blast=True  # Fast mode
)

# Access top candidate
top_candidate = result["validated_results"][0]
print(f"Forward Primer: {top_candidate['candidate']['fwd_seq']}")
print(f"Reverse Primer: {top_candidate['candidate']['rev_seq']}")
print(f"Quality Score:  {top_candidate['score']} / 100")
print(f"Confidence:     {result['confidence']['confidence_level']}")

# Print ReAct reasoning trace summary
print(result["report"])
```

---

## 🔬 Benchmark Framework

PrimerAgent includes a reproducible benchmarking suite comparing performance across 60 test cases (20 genes × 3 application presets).

Run benchmarks:
```bash
python -m benchmarks.benchmark_runner --fast-mode
```

Generate statistical comparison plots and tables:
```bash
python -m benchmarks.analysis
```

---

## 📊 PrimerAgent vs PrimeGen

For a detailed 17-dimension comparison with PrimeGen (Zhao et al., *Nature Biomedical Engineering*, 2025), see [docs/primegen_comparison.md](docs/primegen_comparison.md).

Key differences:
- **Architecture**: Single ReAct Agent vs. Multi-Agent Orchestrator
- **LLM Engine**: Google Gemini vs. OpenAI GPT-4o
- **Transparency**: Full public Reasoning Traces vs. Internal Agent Communication
- **Domain**: General PCR (Standard, qPCR, Sanger) vs. High-throughput tNGS

---

## 📖 Citation & Publication Documentation

- [System Architecture](docs/architecture.md)
- [PrimeGen Comparative Analysis](docs/primegen_comparison.md)
- [Reviewer Response Document](docs/reviewer_response.md)
- [Novelty & Contribution Analysis](docs/novelty_analysis.md)

---

## 📄 License

Distributed under the MIT License. See `LICENSE` for more information.
