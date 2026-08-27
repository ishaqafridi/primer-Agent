"""
PrimerAgent Confidence Scorer — LLM-Based Biological Confidence Assessment

Provides confidence scoring that goes beyond numerical metrics by incorporating
biological reasoning from Gemini. This is a novel feature not present in
PrimeGen or conventional primer design tools.

The confidence scorer evaluates:
    - Thermodynamic suitability for the target application
    - Sequence composition and potential issues
    - Expected experimental performance
    - Biological context (gene function, organism)
"""

import json
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


class ConfidenceScorer:
    """
    LLM-enhanced confidence scoring for primer designs.
    
    Combines the numerical quality score (0-100) with Gemini's biological
    reasoning to produce a confidence assessment that explains WHY a primer
    pair is expected to work well (or poorly) in the target experiment.
    
    Attributes:
        gemini_client: GeminiClient instance for LLM reasoning.
    """

    def __init__(self, gemini_client=None):
        """
        Initialize the confidence scorer.
        
        Args:
            gemini_client: Optional GeminiClient. If None, scoring will use
                           heuristic-only mode without LLM reasoning.
        """
        self.gemini_client = gemini_client

    def compute_heuristic_confidence(
        self, evaluation: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Compute a heuristic confidence score without LLM.
        
        Maps the quality score (0-100) to a confidence level with
        interpretive labels.
        
        Args:
            evaluation: Primer evaluation result dictionary.
            
        Returns:
            Dictionary with confidence_score (0.0-1.0), confidence_level,
            and reasoning based on evaluation metrics.
        """
        score = evaluation.get("score", 0)
        failures = evaluation.get("failures", [])
        breakdown = evaluation.get("breakdown", {})

        # Map score to confidence (0.0 - 1.0)
        confidence = min(1.0, score / 100.0)

        # Penalize specific critical failures
        critical_issues = []
        if breakdown.get("blast_pts", 25) < 15:
            confidence *= 0.7
            critical_issues.append("Low specificity — potential off-target amplification")
        if breakdown.get("hairpin_pts", 10) == 0:
            confidence *= 0.85
            critical_issues.append("Significant hairpin formation risk")
        if breakdown.get("dimer_pts", 10) < 5:
            confidence *= 0.85
            critical_issues.append("Primer-dimer formation likely")
        if breakdown.get("tm_diff_pts", 15) < 10:
            confidence *= 0.9
            critical_issues.append("Tm imbalance may affect amplification efficiency")

        confidence = round(confidence, 3)

        # Determine confidence level
        if confidence >= 0.85:
            level = "HIGH"
            summary = "Primer pair is expected to perform well in the target application."
        elif confidence >= 0.65:
            level = "MODERATE"
            summary = "Primer pair should work but may require optimization of PCR conditions."
        elif confidence >= 0.45:
            level = "LOW"
            summary = "Primer pair has significant issues. Consider redesign or careful optimization."
        else:
            level = "VERY LOW"
            summary = "Primer pair is unlikely to perform well. Redesign recommended."

        reasons = []
        if not failures:
            reasons.append("All quality criteria passed.")
        else:
            reasons.extend(failures[:3])  # Top 3 failures

        if critical_issues:
            reasons.extend(critical_issues)

        return {
            "confidence_score": confidence,
            "confidence_level": level,
            "summary": summary,
            "reasons": reasons,
            "quality_score": score,
            "method": "heuristic",
        }

    def compute_llm_confidence(
        self,
        evaluation: Dict[str, Any],
        gene_name: str = "",
        organism: str = "",
        application: str = "",
    ) -> Dict[str, Any]:
        """
        Compute LLM-enhanced confidence score using Gemini.
        
        Asks Gemini to provide a biological confidence assessment that
        considers the specific gene, organism, and application context.
        
        Args:
            evaluation: Primer evaluation result dictionary.
            gene_name: Target gene symbol.
            organism: Target organism.
            application: PCR application type.
            
        Returns:
            Dictionary with confidence_score, confidence_level, biological
            reasoning, and experiment recommendations.
        """
        # Start with heuristic score
        heuristic = self.compute_heuristic_confidence(evaluation)

        if not self.gemini_client or not self.gemini_client.api_key:
            return heuristic

        candidate = evaluation.get("candidate", {})
        prompt = f"""As an expert molecular biologist, assess the confidence level for this primer pair:

Target: {gene_name} in {organism}
Application: {application}

Forward Primer: {candidate.get('fwd_seq', 'N/A')} (Tm={candidate.get('fwd_tm', 0)}°C, GC={candidate.get('fwd_gc', 0)}%)
Reverse Primer: {candidate.get('rev_seq', 'N/A')} (Tm={candidate.get('rev_tm', 0)}°C, GC={candidate.get('rev_gc', 0)}%)
Product Size: {candidate.get('product_size', 0)} bp
Quality Score: {evaluation.get('score', 0)}/100
Failures: {json.dumps(evaluation.get('failures', []))}

Provide your assessment as JSON with these fields:
- confidence_score: float 0.0-1.0
- confidence_level: "HIGH", "MODERATE", "LOW", or "VERY LOW"
- biological_reasoning: string explaining biological assessment
- experiment_recommendations: list of 2-3 specific wet-lab tips
- potential_issues: list of any biological concerns

Respond ONLY with valid JSON, no other text."""

        try:
            response_text = self.gemini_client.invoke(
                prompt,
                system_prompt="You are an expert molecular biologist evaluating PCR primers.",
            )

            llm_result = self.gemini_client.extract_json(response_text)

            # Merge with heuristic
            return {
                "confidence_score": llm_result.get("confidence_score", heuristic["confidence_score"]),
                "confidence_level": llm_result.get("confidence_level", heuristic["confidence_level"]),
                "summary": llm_result.get("biological_reasoning", heuristic["summary"]),
                "reasons": heuristic["reasons"],
                "experiment_recommendations": llm_result.get("experiment_recommendations", []),
                "potential_issues": llm_result.get("potential_issues", []),
                "quality_score": evaluation.get("score", 0),
                "method": "gemini_enhanced",
            }

        except Exception as e:
            logger.warning(f"LLM confidence scoring failed: {e}. Falling back to heuristic.")
            heuristic["method"] = "heuristic_fallback"
            return heuristic

