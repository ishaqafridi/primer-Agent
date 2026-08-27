"""
Tool 4: Amplicon Validator — PCR Product Size & Specificity Audit

Interprets In-Silico PCR results against application constraints (e.g., qPCR amplicon size 80–200 bp).
Evaluates amplicon size compatibility, product multiplicity, off-target products, and target identity.

References:
    - qPCR amplicon criteria: Bustin et al., Clinical Chemistry, 2009
"""

import json
import logging
from typing import Dict, Any, Tuple, Optional, List

from langchain_core.tools import tool

logger = logging.getLogger(__name__)

# Application Amplicon Size Constraints (min_bp, max_bp)
APPLICATION_AMPLICON_BOUNDS: Dict[str, Tuple[int, int]] = {
    "qPCR": (80, 200),
    "Standard PCR": (100, 500),
    "Sanger Sequencing": (300, 1000),
    "High-GC Preset": (80, 300),
}


def _validate_amplicon_impl(
    pcr_result: Dict[str, Any],
    application: str = "Standard PCR",
    expected_size_range: Optional[Tuple[int, int]] = None,
) -> Dict[str, Any]:
    """
    Interpret In-Silico PCR output against amplicon quality criteria.
    
    Args:
        pcr_result: Dictionary returned from InSilicoPCRTool.
        application: Application preset name (qPCR, Standard PCR, Sanger Sequencing).
        expected_size_range: Optional explicit amplicon size bounds (min, max) bp.
        
    Returns:
        Structured amplicon evaluation result.
    """
    min_bp, max_bp = expected_size_range or APPLICATION_AMPLICON_BOUNDS.get(application, (100, 300))

    status = pcr_result.get("status", "FAIL")
    amp_count = pcr_result.get("amplicon_count", 0)
    amp_size = pcr_result.get("amplicon_size", 0)
    amplicons = pcr_result.get("amplicons", [])
    reason = pcr_result.get("reason", "")

    failures = []
    warnings = []

    # 1. Product Multiplicity Check
    if amp_count == 0:
        failures.append("In-Silico PCR generated 0 amplicons (no amplification).")
    elif amp_count > 1:
        failures.append(f"In-Silico PCR generated multiple amplicons ({amp_count} products detected).")

    # 2. Amplicon Size Range Check
    if amp_count >= 1:
        if not (min_bp <= amp_size <= max_bp):
            failures.append(
                f"Amplicon size ({amp_size} bp) is outside configured {application} size range ({min_bp}–{max_bp} bp)."
            )

    # 3. Off-target Amplicons
    if len(amplicons) > 1:
        off_target_sizes = [a["amplicon_size"] for a in amplicons[1:]]
        warnings.append(f"Off-target amplicons detected with sizes: {off_target_sizes} bp.")

    is_valid = len(failures) == 0 and status == "PASS"

    return {
        "status": "PASS" if is_valid else "FAIL",
        "application": application,
        "expected_size_range": [min_bp, max_bp],
        "observed_amplicon_size": amp_size,
        "amplicon_count": amp_count,
        "specific_product": amp_count == 1,
        "orientation_correct": pcr_result.get("orientation") == "correct",
        "failures": failures,
        "warnings": warnings,
        "details": f"Amplicon {amp_size} bp ({'PASS' if is_valid else 'FAIL'}). Expected: {min_bp}-{max_bp} bp. Products: {amp_count}.",
    }


@tool
def validate_amplicon(
    pcr_result_json: str,
    application: str = "Standard PCR",
    min_size: int = 100,
    max_size: int = 300,
) -> str:
    """Validate In-Silico PCR amplicon size and product specificity.
    
    Use this tool after running in_silico_pcr to evaluate whether the produced amplicon
    meets the specific application size constraints (e.g. 80-200 bp for qPCR).
    
    Args:
        pcr_result_json: JSON string of In-Silico PCR output.
        application: PCR application preset name.
        min_size: Minimum acceptable amplicon size in bp.
        max_size: Maximum acceptable amplicon size in bp.
    
    Returns:
        JSON string with amplicon validation pass/fail status and detailed reasons.
    """
    try:
        pcr_res = json.loads(pcr_result_json)
    except (json.JSONDecodeError, TypeError):
        pcr_res = {}

    result = _validate_amplicon_impl(
        pcr_result=pcr_res,
        application=application,
        expected_size_range=(min_size, max_size),
    )
    return json.dumps(result, indent=2)
