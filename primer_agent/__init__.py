"""
🧬 PrimerAgent — Autonomous ReAct-Based PCR Primer Design & Validation Agent

A single-agent AI system powered by Google Gemini that uses the ReAct
(Reasoning + Acting) paradigm to autonomously design, validate, and optimize
PCR primers through iterative biological reasoning.

Architecture:
    Single ReAct Agent → [7 Bioinformatics Tools] → Gemini Reasoning Engine
    
Key Components:
    - react_agent: Core ReAct reasoning loop with Gemini
    - gemini_client: Google Gemini API client with retry/rate-limit
    - tools/: 7 specialized bioinformatics tools
    - database/: Primer design persistence layer
    - reasoning/: Thought/Action/Observation trace system
"""

__version__ = "2.0.0"
__author__ = "PrimerAgent Team"
__description__ = "ReAct-Based AI Agent for Autonomous PCR Primer Design"
