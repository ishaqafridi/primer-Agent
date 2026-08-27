"""
🧬 PrimerAgent v2.0 — Streamlit Application Entry Point

A ReAct-based AI agent for autonomous PCR primer design, powered by
Google Gemini. Features real-time reasoning trace visualization, 
confidence scoring, and an integrated primer database.

Usage:
    streamlit run app.py
"""

import os
import json
import time
import logging
from datetime import datetime

import streamlit as st
import pandas as pd

from primer_agent.config import (
    ACCEPTANCE_CRITERIA,
    DEFAULT_PRESETS,
    SUPPORTED_ORGANISMS,
    GEMINI_CONFIG,
)
from primer_agent.react_agent import PrimerReActAgent
from primer_agent.database.sqlite_store import PrimerDatabase

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ==============================================================================
# PAGE CONFIGURATION
# ==============================================================================

def main():
    st.set_page_config(
        page_title="PrimerAgent v3.0 — In-Silico PCR Validation",
        page_icon="🧬",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    # Initialize database
    if "db" not in st.session_state:
        db_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "primer_designs.db",
        )
        st.session_state.db = PrimerDatabase(db_path)

    # Define Pages using st.Page
    page_design = st.Page(
        render_design_page,
        title="Primer design",
        icon=":material/biotech:",
        default=True,
    )
    page_db = st.Page(
        render_database_page,
        title="Database",
        icon=":material/database:",
    )
    page_arch = st.Page(
        render_architecture_page,
        title="Architecture",
        icon=":material/schema:",
    )

    pg = st.navigation([page_design, page_db, page_arch], position="sidebar")
    pg.run()


# ==============================================================================
# SIDEBAR
# ==============================================================================

def render_sidebar():
    """Render the sidebar with credentials and settings."""
    with st.sidebar:
        st.header(":material/settings: Configuration")

        # Gemini API Key
        gemini_key = st.text_input(
            "Google Gemini API key",
            value=os.environ.get("GOOGLE_API_KEY", ""),
            type="password",
            help="Required for AI-powered reasoning. Get a key at https://ai.google.dev/",
        )

        # NCBI credentials
        with st.expander(":material/key: NCBI settings"):
            ncbi_email = st.text_input(
                "NCBI email",
                value=os.environ.get("NCBI_EMAIL", "user@example.com"),
            )
            ncbi_api_key = st.text_input(
                "NCBI API key (optional)",
                value=os.environ.get("NCBI_API_KEY", ""),
                type="password",
            )

        # Performance options
        st.divider()
        st.subheader(":material/speed: Performance")
        skip_blast = st.checkbox(
            "Fast mode (skip BLAST)",
            value=True,
            help="Skips NCBI web BLAST queries. Enable for faster design cycles during development.",
        )

        # Gemini model selection
        model_name = st.selectbox(
            "Gemini model",
            ["gemini-1.5-flash", "gemini-2.0-flash", "gemini-1.5-pro", "gemini-2.5-flash"],
            index=0,
            help="gemini-1.5-flash is the primary recommended model for fast, robust reasoning.",
        )

        # Acceptance criteria display
        st.divider()
        with st.expander(":material/checklist: Acceptance criteria"):
            st.markdown(f"""
- **Tm range**: {ACCEPTANCE_CRITERIA['tm_min']}°C – {ACCEPTANCE_CRITERIA['tm_max']}°C
- **GC content**: {ACCEPTANCE_CRITERIA['gc_min']}% – {ACCEPTANCE_CRITERIA['gc_max']}%
- **GC clamp**: {ACCEPTANCE_CRITERIA['gc_clamp_min']} – {ACCEPTANCE_CRITERIA['gc_clamp_max']} G/C in last 5bp
- **Hairpin MFE**: > {ACCEPTANCE_CRITERIA['hairpin_mfe_min']} kcal/mol
- **Dimer MFE**: > {ACCEPTANCE_CRITERIA['self_dimer_mfe_min']} kcal/mol
- **Min score**: ≥ {ACCEPTANCE_CRITERIA['min_pass_score']} / 100
""")

    return {
        "gemini_key": gemini_key,
        "ncbi_email": ncbi_email,
        "ncbi_api_key": ncbi_api_key,
        "skip_blast": skip_blast,
        "model_name": model_name,
    }


# ==============================================================================
# DESIGN PAGE
# ==============================================================================

def render_design_page():
    """Render the main primer design page."""
    settings = render_sidebar()

    # Header
    st.title(":material/biotech: PrimerAgent v3.0")
    st.markdown(
        "A **ReAct-based AI agent** that autonomously designs, validates, "
        "and optimizes PCR primers with **In-Silico PCR Validation (UCSC / Local Engine)** using Google Gemini and Biopython."
    )

    # Mode indicator
    if settings["gemini_key"]:
        st.success(":material/robot: **AI mode active** — Gemini will reason about primer design decisions")
    else:
        st.info(":material/bolt: **Deterministic mode** — Running without AI reasoning (set Gemini API key to enable)")

    st.divider()

    # Input form
    col1, col2 = st.columns(2)

    with col1:
        gene_name = st.text_input(
            "Gene symbol or accession ID",
            value="BRCA1",
            placeholder="e.g., BRCA1, TP53, GAPDH, NM_007294",
            help="Enter a standard gene symbol or NCBI nucleotide accession number.",
        )
        organism_option = st.selectbox(
            "Target organism",
            options=SUPPORTED_ORGANISMS,
            index=0,
        )
        if organism_option == "Other / Custom Organism":
            organism = st.text_input(
                "Custom organism name",
                value="",
                placeholder="e.g., Oryza sativa, Zea mays",
            ).strip()
        else:
            organism = organism_option.split(" (")[0]

    with col2:
        application = st.selectbox(
            "Application preset",
            options=["Standard PCR", "qPCR", "Sanger Sequencing"],
            index=0,
        )
        product_size = (100, 300)
        num_return = st.slider(
            "Number of primer pairs",
            min_value=1,
            max_value=10,
            value=10,
            step=1,
            help="Number of validated primer pairs to return (up to 10).",
        )

    st.markdown("")
    start_button = st.button(
        "🚀 Run PrimerAgent",
        type="primary",
        width="stretch",
    )

    if start_button:
        if not gene_name.strip():
            st.error("Please enter a valid gene symbol or accession ID.")
            return
        if not organism:
            st.error("Please enter a valid organism name.")
            return

        run_agent(
            gene_name=gene_name.strip(),
            organism=organism,
            application=application,
            product_size_range=product_size,
            num_return=num_return,
            settings=settings,
        )


# ==============================================================================
# AGENT EXECUTION
# ==============================================================================

def run_agent(
    gene_name: str,
    organism: str,
    application: str,
    product_size_range: tuple,
    num_return: int,
    settings: dict,
):
    """Execute the ReAct agent and display results."""

    # Initialize agent
    agent = PrimerReActAgent(
        api_key=settings["gemini_key"],
        model_name=settings["model_name"],
    )

    # Progress and reasoning display
    progress_bar = st.progress(0, text="Initializing PrimerAgent...")
    reasoning_container = st.container()
    results_container = st.container()

    # Reasoning step counter for progress
    step_count = [0]
    total_expected_steps = 12  # Approximate

    def on_step(step_dict):
        """Callback for live reasoning trace updates."""
        step_count[0] += 1
        progress = min(95, int(step_count[0] / total_expected_steps * 100))
        step_type = step_dict.get("type", "unknown")
        content_preview = step_dict.get("content", "")[:100]
        progress_bar.progress(progress, text=f"Step {step_count[0]}: {step_type} — {content_preview}")

    # Run the agent
    start_time = time.time()
    with st.spinner("PrimerAgent is reasoning..."):
        result = agent.run(
            gene_name=gene_name,
            organism=organism,
            application=application,
            product_size_range=product_size_range,
            num_return=num_return,
            skip_blast=settings["skip_blast"],
            email=settings["ncbi_email"],
            ncbi_api_key=settings["ncbi_api_key"] if settings["ncbi_api_key"] else None,
            on_step_callback=on_step,
        )
    elapsed = round(time.time() - start_time, 1)

    progress_bar.progress(100, text=f"Design complete in {elapsed}s")

    # Display reasoning trace
    with reasoning_container:
        st.subheader(":material/psychology: ReAct reasoning trace")
        trace_steps = result.get("reasoning_trace", [])
        
        if trace_steps:
            for step in trace_steps:
                step_type = step.get("type", "unknown")
                step_num = step.get("step_number", "?")
                timestamp = step.get("timestamp", "")
                content = step.get("content", "")

                if step_type == "thought":
                    with st.chat_message("assistant", avatar="💭"):
                        st.markdown(f"**Step {step_num} — Agent Thought** *({timestamp})*")
                        st.markdown(content)
                elif step_type == "action":
                    with st.chat_message("user", avatar="⚡"):
                        st.markdown(f"**Step {step_num} — Selected Action** *({timestamp})*")
                        st.code(content, language="json")
                elif step_type == "observation":
                    with st.chat_message("system", avatar="👁️"):
                        st.markdown(f"**Step {step_num} — Observation** *({timestamp})*")
                        # Truncate long observations
                        if len(content) > 1000:
                            st.code(content[:1000] + "\n...(truncated)", language="json")
                        else:
                            st.code(content, language="json")
                elif step_type == "final_answer":
                    with st.chat_message("assistant", avatar="✅"):
                        st.markdown(f"**Step {step_num} — Final Answer** *({timestamp})*")
                        st.markdown(content)
                else:
                    with st.chat_message("system", avatar="⚙️"):
                        st.markdown(content)

    st.divider()

    # Display results
    with results_container:
        validated_list = result.get("validated_results", [])
        st.subheader(":material/target: Validated primer pairs")

        # Confidence display
        confidence = result.get("confidence")
        if confidence:
            conf_score = confidence.get("confidence_score", 0)
            conf_level = confidence.get("confidence_level", "N/A")
            conf_color = {
                "HIGH": "green",
                "MODERATE": "orange",
                "LOW": "red",
                "VERY LOW": "red",
            }.get(conf_level, "gray")

            col_a, col_b, col_c = st.columns(3)
            with col_a:
                st.metric("Best score", f"{result.get('best_score', 0)} / 100")
            with col_b:
                st.metric("Confidence", f"{conf_score:.2f} ({conf_level})")
            with col_c:
                st.metric("Execution time", f"{elapsed}s")

            if confidence.get("summary"):
                st.info(f"🧬 **Biological assessment:** {confidence['summary']}")

        # Evaluation statistics
        num_requested = result.get("num_requested", 0)
        num_returned = result.get("num_returned", 0)
        total_evaluated = result.get("total_evaluated", 0)
        total_passed = result.get("total_passed", 0)
        total_failed = result.get("total_failed", 0)
        design_passed = result.get("design_passed", False)

        if design_passed:
            st.success(
                f"🟢 **{num_returned} VALID PRIMER PAIR(S) RETURNED** out of {num_requested} requested — "
                f"Evaluated {total_evaluated} candidates, {total_passed} passed, {total_failed} rejected."
            )
        else:
            st.error(
                f"🔴 **NO VALID PRIMER PAIRS FOUND** — "
                f"Evaluated {total_evaluated} candidates, ALL {total_failed} FAILED critical QC checks. "
                f"Review the reasoning trace for details."
            )

        # Display only VALID (PASS) primer pair tabs — never show failed candidates
        if validated_list:
            tab_titles = [f"✅ Valid Pair #{i}" for i in range(1, len(validated_list) + 1)]
            tabs = st.tabs(tab_titles)

            for idx, (tab, res) in enumerate(zip(tabs, validated_list), 1):
                with tab:
                    render_candidate(res, idx)

        # Save to database
        st.divider()
        if st.button("Save to PrimerAgent database", icon=":material/save:", width="stretch"):
            db = st.session_state.db
            saved_ids = db.save_from_agent_result(result)
            st.success(f"Saved {len(saved_ids)} primer design(s) to database (IDs: {saved_ids})")

        # Download report
        report_text = result.get("report", "")
        if report_text:
            st.download_button(
                label="Download validation report",
                data=report_text,
                file_name=f"PrimerAgent_Report_{gene_name}_{datetime.now().strftime('%Y%m%d')}.txt",
                mime="text/plain",
                icon=":material/download:",
                width="stretch",
            )

        # Gemini usage stats
        usage = result.get("gemini_usage", {})
        if usage.get("total_requests", 0) > 0:
            with st.expander("📊 Gemini API usage"):
                st.json(usage)


def render_candidate(res: dict, idx: int):
    """Render a single primer candidate card."""
    cand = res.get("candidate", {})
    score = res.get("score", 0)
    pass_flag = res.get("pass", False)

    pcr_res = res.get("pcr_result", {})
    exon_res = res.get("exon_result", {})
    pcr_status = pcr_res.get("status", "PASS")
    pcr_count = pcr_res.get("amplicon_count", 1)
    pcr_engine = pcr_res.get("engine_used", "Local Engine")

    st.markdown(
        f"🧪 **Gate 2 In-Silico PCR:** `{'🟢 PASS' if pcr_status == 'PASS' else '🔴 FAIL'}` ({pcr_count} product(s) via {pcr_engine}) "
        f"| 🧬 **gDNA Risk:** `{exon_res.get('genomic_dna_risk', 'reduced')}`"
    )

    m1, m2, m3, m4 = st.columns(4)
    with m1:
        st.metric("Quality score", f"{score} / 100")
    with m2:
        st.metric("Status", "🟢 PASS" if pass_flag else "🔴 FAIL")
    with m3:
        st.metric("Product size", f"{cand.get('product_size', 0)} bp")
    with m4:
        st.metric("Tm difference", f"{cand.get('tm_diff', 0)}°C")

    # GC clamp values
    fwd_clamp = res.get("fwd_gc_clamp", {})
    rev_clamp = res.get("rev_gc_clamp", {})
    fwd_clamp_gc = fwd_clamp.get("gc_count", "N/A") if isinstance(fwd_clamp, dict) else "N/A"
    rev_clamp_gc = rev_clamp.get("gc_count", "N/A") if isinstance(rev_clamp, dict) else "N/A"
    fwd_clamp_pass = fwd_clamp.get("pass", True) if isinstance(fwd_clamp, dict) else True
    rev_clamp_pass = rev_clamp.get("pass", True) if isinstance(rev_clamp, dict) else True

    # Primer sequences
    p1, p2 = st.columns(2)
    with p1:
        st.markdown("**Forward primer (5' → 3')**")
        st.code(cand.get("fwd_seq", ""), language="text")
        st.caption(
            f"Length: {cand.get('fwd_len', len(cand.get('fwd_seq', '')))} bp · "
            f"Tm: {cand.get('fwd_tm', 0)}°C · "
            f"GC: {cand.get('fwd_gc', 0)}% · "
            f"3' GC Clamp: {fwd_clamp_gc} G/C ({'PASS' if fwd_clamp_pass else 'FAIL'})"
        )
    with p2:
        st.markdown("**Reverse primer (5' → 3')**")
        st.code(cand.get("rev_seq", ""), language="text")
        st.caption(
            f"Length: {cand.get('rev_len', len(cand.get('rev_seq', '')))} bp · "
            f"Tm: {cand.get('rev_tm', 0)}°C · "
            f"GC: {cand.get('rev_gc', 0)}% · "
            f"3' GC Clamp: {rev_clamp_gc} G/C ({'PASS' if rev_clamp_pass else 'FAIL'})"
        )

    # Quality control audit
    with st.expander(":material/analytics: Quality control audit"):
        fwd_tm = cand.get("fwd_tm", 0.0)
        rev_tm = cand.get("rev_tm", 0.0)
        fwd_gc = cand.get("fwd_gc", 0.0)
        rev_gc = cand.get("rev_gc", 0.0)
        tm_diff = cand.get("tm_diff", 0.0)
        fwd_struct = res.get("fwd_struct", {})
        rev_struct = res.get("rev_struct", {})
        hetero_struct = res.get("hetero_struct", {})
        fwd_blast = res.get("fwd_blast", {})
        rev_blast = res.get("rev_blast", {})

        qc_data = {
            "Check": [
                "Tm range (57-63°C)",
                "GC content (40-60%)",
                "GC Clamp 3' End (1-3 G/C)",
                "Tm difference (≤ 2°C)",
                "BLAST off-targets (≤ 1)",
                "Hairpin MFE (> -2.0)",
                "Self-dimer MFE (> -6.0)",
                "Hetero-dimer MFE (> -6.0)",
            ],
            "Forward": [
                f"{fwd_tm}°C",
                f"{fwd_gc}%",
                f"{fwd_clamp_gc} G/C in last 5bp",
                f"{tm_diff}°C",
                f"{fwd_blast.get('off_target_hits', 0)} hits" if isinstance(fwd_blast, dict) else "0 hits",
                f"{fwd_struct.get('hairpin_mfe', 'N/A')} kcal/mol",
                f"{fwd_struct.get('self_dimer_mfe', 'N/A')} kcal/mol",
                f"{hetero_struct.get('hetero_dimer_mfe', 'N/A')} kcal/mol",
            ],
            "Reverse": [
                f"{rev_tm}°C",
                f"{rev_gc}%",
                f"{rev_clamp_gc} G/C in last 5bp",
                "—",
                f"{rev_blast.get('off_target_hits', 0)} hits" if isinstance(rev_blast, dict) else "0 hits",
                f"{rev_struct.get('hairpin_mfe', 'N/A')} kcal/mol",
                f"{rev_struct.get('self_dimer_mfe', 'N/A')} kcal/mol",
                "—",
            ],
            "Result": [
                "🟢" if (57 <= fwd_tm <= 63 and 57 <= rev_tm <= 63) else "🔴",
                "🟢" if (40 <= fwd_gc <= 60 and 40 <= rev_gc <= 60) else "🔴",
                "🟢" if (fwd_clamp_pass and rev_clamp_pass) else "🔴",
                "🟢" if tm_diff <= 2.0 else "🔴",
                "🟢" if (not isinstance(fwd_blast, dict) or not isinstance(rev_blast, dict) or (fwd_blast.get("off_target_hits", 0) <= 1 and rev_blast.get("off_target_hits", 0) <= 1)) else "🔴",
                "🟢" if (fwd_struct.get("hairpin_pass", True) and rev_struct.get("hairpin_pass", True)) else "🔴",
                "🟢" if (fwd_struct.get("self_dimer_pass", True) and rev_struct.get("self_dimer_pass", True)) else "🔴",
                "🟢" if hetero_struct.get("hetero_dimer_pass", True) else "🔴",
            ],
        }
        st.dataframe(pd.DataFrame(qc_data), hide_index=True, width="stretch")

        failures = res.get("failures", [])
        if failures:
            st.markdown("**Failure details:**")
            for f in failures:
                st.markdown(f"- ⚠️ {f}")


# ==============================================================================
# DATABASE PAGE
# ==============================================================================

# ==============================================================================
# DATABASE PAGE
# ==============================================================================

def render_database_page():
    """Render the fully functional primer database browser and management system."""
    st.title(":material/database: PrimerAgent database")
    st.markdown("Browse, inspect, manage, and export validated primer designs stored in the local SQLite database.")

    db = st.session_state.db
    stats = db.get_stats()

    # Stats cards
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.metric("Total designs", stats["total_designs"])
    with c2:
        st.metric("Passed designs (≥60)", stats["passed_designs"])
    with c3:
        st.metric("Pass rate", f"{stats['pass_rate']}%")
    with c4:
        st.metric("Unique genes", stats["unique_genes"])

    st.divider()

    # Search filters
    col1, col2, col3 = st.columns(3)
    with col1:
        search_gene = st.text_input("Filter by gene symbol", placeholder="e.g., BRCA1, TP53, GAPDH")
    with col2:
        search_organism = st.text_input("Filter by organism", placeholder="e.g., Homo sapiens")
    with col3:
        min_score = st.number_input("Minimum quality score", min_value=0, max_value=100, value=0, step=10)

    # Query database
    results = db.search(
        gene_symbol=search_gene if search_gene else None,
        organism=search_organism if search_organism else None,
        min_score=min_score if min_score > 0 else None,
    )

    if results:
        # Table view
        display_cols = [
            "id", "gene_symbol", "organism", "application",
            "fwd_sequence", "rev_sequence", "quality_score",
            "in_silico_pcr_status", "amplicon_length", "created_at",
        ]
        df = pd.DataFrame(results)
        available_cols = [c for c in display_cols if c in df.columns]
        st.dataframe(df[available_cols], hide_index=True, width="stretch")

        st.divider()

        # In-browser CSV and JSON export buttons
        e_col1, e_col2 = st.columns(2)
        with e_col1:
            csv_data = db.export_csv_str(
                gene_symbol=search_gene if search_gene else None,
                organism=search_organism if search_organism else None,
                min_score=min_score if min_score > 0 else None,
            )
            st.download_button(
                label="📥 Download CSV export",
                data=csv_data,
                file_name=f"PrimerAgent_DB_Export_{datetime.now().strftime('%Y%m%d')}.csv",
                mime="text/csv",
                width="stretch",
            )
        with e_col2:
            json_data = db.export_json_str(
                gene_symbol=search_gene if search_gene else None,
                organism=search_organism if search_organism else None,
                min_score=min_score if min_score > 0 else None,
            )
            st.download_button(
                label="📥 Download JSON export",
                data=json_data,
                file_name=f"PrimerAgent_DB_Export_{datetime.now().strftime('%Y%m%d')}.json",
                mime="application/json",
                width="stretch",
            )

        # Record Inspector & Management Section
        st.divider()
        st.subheader(":material/find_in_page: Record inspector & management")

        record_ids = [r["id"] for r in results]
        selected_id = st.selectbox("Select Record ID to inspect or manage", record_ids)

        selected_record = db.get_by_id(selected_id)
        if selected_record:
            rec_col1, rec_col2 = st.columns(2)
            with rec_col1:
                st.markdown(f"**Gene Symbol:** `{selected_record.get('gene_symbol')}`")
                st.markdown(f"**Organism:** `{selected_record.get('organism')}`")
                st.markdown(f"**Genome Assembly:** `{selected_record.get('genome_assembly')}`")
                st.markdown(f"**Application:** `{selected_record.get('application')}`")
                st.markdown(f"**Quality Score:** `{selected_record.get('quality_score')} / 100`")
                st.markdown(f"**In-Silico PCR:** `{selected_record.get('in_silico_pcr_status')}` ({selected_record.get('amplicon_count')} product via {selected_record.get('in_silico_pcr_engine')})")

            with rec_col2:
                st.markdown("**Forward Primer (5' → 3'):**")
                st.code(selected_record.get("fwd_sequence", ""), language="text")
                st.caption(f"Tm: {selected_record.get('fwd_tm')}°C · GC: {selected_record.get('fwd_gc')}%")

                st.markdown("**Reverse Primer (5' → 3'):**")
                st.code(selected_record.get("rev_sequence", ""), language="text")
                st.caption(f"Tm: {selected_record.get('rev_tm')}°C · GC: {selected_record.get('rev_gc')}%")

            # Deletion action
            if st.button("🗑️ Delete Selected Record from Database", type="secondary"):
                if db.delete_design(selected_id):
                    st.success(f"Deleted primer record #{selected_id} successfully.")
                    st.rerun()
                else:
                    st.error("Failed to delete record.")

    else:
        st.info("No primer designs found in database. Run the agent to generate and save designs.")


# ==============================================================================
# ARCHITECTURE PAGE
# ==============================================================================

def render_architecture_page():
    """Render the system architecture documentation page."""
    st.title("🏗️ PrimerAgent v3.0 architecture")
    st.markdown("### ReAct-Based Single-Agent AI System with 11 Bioinformatics Tools & Gate 2 In-Silico PCR")

    st.markdown("""
**PrimerAgent v3.0** implements a genuine **ReAct (Reasoning + Acting)** architecture 
where Google Gemini autonomously decides which bioinformatics tool to invoke at each 
step, using strict multi-gate validation (Gate 2 In-Silico PCR) and a zero-config SQLite database store.

---

#### System Architecture & Workflow Diagram
""")

    st.code("""
┌────────────────────────────────────────────────────────────────────────────────┐
│                           PrimerAgent v3.0 Architecture                        │
│                 Single-Agent ReAct + In-Silico PCR Gate + SQLite               │
├────────────────────────────────────────────────────────────────────────────────┤
│                                                                                │
│  User Request: "Design primers for BRCA1 in Homo sapiens for qPCR (100-300bp)" │
│       │                                                                        │
│       ▼                                                                        │
│  ┌──────────────────────────────────┐                                         │
│  │     Google Gemini LLM Engine     │◄──── System Prompt                       │
│  │   (Reasoning + Tool Selection)   │      (Expert AI Bioinformatician v3.0)   │
│  └──────────┬───────────────────────┘                                         │
│             │                                                                  │
│             ▼                                                                  │
│  ┌──────────────────────────────────┐                                         │
│  │      ReAct Reasoning Loop        │                                         │
│  │                                  │                                         │
│  │  THOUGHT → ACTION → OBSERVATION  │                                         │
│  │       ↑                  │       │                                         │
│  │       └──────────────────┘       │                                         │
│  │      (Iterative Optimization)    │                                         │
│  └──────────┬───────────────────────┘                                         │
│             │                                                                  │
│             ▼                                                                  │
│  ┌──────────────────────────────────────────────────────────────────────────┐ │
│  │                     Tool Suite (11 Integrated Tools)                     │ │
│  ├──────────────────────────────────────────────────────────────────────────┤ │
│  │ 1. RESOLVE_TARGET     │ Genome assembly (GRCh38/GRCm39) & accession      │ │
│  │ 2. FETCH_SEQUENCE     │ NCBI Entrez sequence retrieval & offline backup │ │
│  │ 3. DESIGN_PRIMERS     │ Primer-BLAST candidate generator (50 candidates)│ │
│  │ 4. IN_SILICO_PCR      │ GATE 2: UCSC API / Local Reference PCR Engine   │ │
│  │ 5. VALIDATE_AMPLICON  │ Amplicon size & product count validation         │ │
│  │ 6. CHECK_BLAST        │ BLAST off-target specificity checker             │ │
│  │ 7. CHECK_STRUCTURE    │ Hairpin MFE & Self-Dimer thermodynamic checker   │ │
│  │ 8. CHECK_HETERODIMER  │ Hetero-Dimer cross-interaction checker           │ │
│  │ 9. VALIDATE_EXON      │ Exon-exon junction & gDNA contamination auditor  │ │
│  │ 10. EVALUATE_PRIMERS  │ Strict Scorer (REJECT 0-59 vs ELIGIBLE 60-100)   │ │
│  │ 11. ADJUST_PARAMETERS │ Intelligent Parameter Critic & Optimizer         │ │
│  └──────────────────────────────────────────────────────────────────────────┘ │
│             │                                                                  │
│             ▼                                                                  │
│  ┌──────────────────────────────────────────────────────────────────────────┐ │
│  │                              Output Layer                                │ │
│  ├──────────────────────────────────────────────────────────────────────────┤ │
│  │ • Validated Top N Primer Pairs (PASS-only)                               │ │
│  │ • Quality Scores (60-100) & Complete QC Audit                             │ │
│  │ • Biological Confidence Assessment (Heuristic + LLM)                     │ │
│  │ • Full ReAct Reasoning Trace                                             │ │
│  │ • Wet-Lab Experimental Protocols (Ta, MgCl2, Extension Time)             │ │
│  │ • Zero-Config SQLite Database Store (save, query, export CSV/JSON)       │ │
│  └──────────────────────────────────────────────────────────────────────────┘ │
└────────────────────────────────────────────────────────────────────────────────┘
    """, language="text")

    st.markdown("""
---

#### Strict Multi-Gate Validation & Scoring Pipeline

PrimerAgent v3.0 enforces a strict **Validation-First** policy to guarantee wet-lab reliability:

```
    ┌─────────────────────────┐
    │ 1. DESIGN CANDIDATES    │  Generates 50 candidate pairs with Primer-BLAST
    └────────────┬────────────┘
                 │
                 ▼
    ┌─────────────────────────┐
    │ 2. IN-SILICO PCR GATE   │  GATE 2 HARD VALIDATION GATE: Must yield exactly 1 intended amplicon
    └────────────┬────────────┘
                 │
                 ▼
    ┌─────────────────────────┐
    │ 3. THERMODYNAMIC QC     │  Tm (57-63°C), GC% (40-60%), 3' Clamp, Hairpin MFE, Self/Hetero-Dimer
    └────────────┬────────────┘
                 │
                 ▼
    ┌─────────────────────────┐
    │ 4. REJECT / ELIGIBLE    │  Any Failure → REJECT (Score = NOT SCORED, Excluded from results)
    └────────────┬────────────┘  All Pass → ELIGIBLE (Calculates Quality Score 60–100)
                 │
                 ▼
    ┌─────────────────────────┐
    │ 5. RANK & RETURN TOP N  │  Ranks PASS candidates and returns top user-requested count (1–10)
    └─────────────────────────┘
```

---

#### Comparison: PrimerAgent v3.0 vs PrimeGen Architecture

| Feature | PrimerAgent v3.0 | PrimeGen |
|---------|------------------|----------|
| **Architecture** | Single-Agent ReAct | Multi-Agent Orchestrator |
| **Tool Suite** | 11 Integrated Tools | 4 Dedicated Agents |
| **In-Silico PCR** | Gate 2 (UCSC + Local Reference Engine) | Basic sequence match |
| **Validation Policy** | Strict Validate-First (REJECT Failures) | Numeric score blending |
| **LLM Engine** | Google Gemini (1.5-flash / 2.0-flash) | OpenAI GPT-4o |
| **Reasoning Visibility**| Full Thought→Action→Observation Trace | Internal Agent Messages |
| **Database** | SQLite Store (Query, Inspect, Delete, CSV/JSON) | Not Integrated |
| **Target Use Case** | General PCR, qPCR, Sanger Sequencing | Amplicon sequencing (tNGS) |
""")


# ==============================================================================
# ENTRY POINT
# ==============================================================================

if __name__ == "__main__":
    main()
