"""
Tool 7: Parameter Adjuster — Intelligent Parameter Critic & Optimization

Analyzes specific failure modes from In-Silico PCR, amplicon, specificity, and thermodynamic evaluations,
intelligently modifying Primer-BLAST parameters for the next iteration.

Failure-to-Adjustment Mappings:
    - multiple_amplicons → Increase Primer-BLAST specificity & narrow product size
    - amplicon_too_long  → Reduce maximum amplicon product size limit
    - no_pcr_product    → Relax Tm window & widen target region
    - off_target_binding → Increase 3'-end specificity stringency
    - hairpin           → Reduce hairpin threshold
    - heterodimer       → Tighten cross-primer stability constraints
"""

import json
import logging
from typing import Dict, Any, List, Tuple

from langchain_core.tools import tool
from primer_agent.config import PARAMETER_BOUNDS

logger = logging.getLogger(__name__)


def _adjust_parameters_impl(
    failures: List[str],
    current_params: Dict[str, Any],
) -> Tuple[Dict[str, Any], List[str]]:
    """
    Intelligently modify parameters based on specific failure modes.
    """
    updated_params = dict(current_params)
    logs = []
    joined_failures = " ".join(failures).lower()

    # 1. In-Silico PCR: Multiple Amplicons
    if "multiple amplicons" in joined_failures or "multiple potential pcr" in joined_failures:
        logs.append("Adjusting: Multiple In-Silico PCR products detected. Increasing specificity stringency.")
        min_th = PARAMETER_BOUNDS.get("self_any_th_min", 25.0)
        updated_params["PRIMER_MAX_SELF_ANY_TH"] = max(min_th, updated_params.get("PRIMER_MAX_SELF_ANY_TH", 45.0) - 5.0)

    # 2. In-Silico PCR: Amplicon Too Long / Size Mismatch
    if "outside" in joined_failures and ("size" in joined_failures or "range" in joined_failures):
        logs.append("Adjusting: Amplicon size out of bounds. Adjusting optimal product size parameters.")
        updated_params["PRIMER_OPT_SIZE"] = 20

    # 3. In-Silico PCR: No PCR Product / Binding Failure
    if "0 amplicons" in joined_failures or "failed to bind" in joined_failures or "neither forward nor reverse" in joined_failures:
        logs.append("Adjusting: No In-Silico PCR product formed. Slightly widening Tm range window by ±1.0°C.")
        updated_params["PRIMER_MIN_TM"] = max(50.0, updated_params.get("PRIMER_MIN_TM", 57.0) - 1.0)
        updated_params["PRIMER_MAX_TM"] = min(68.0, updated_params.get("PRIMER_MAX_TM", 63.0) + 1.0)

    # 4. Tm Failure
    if "tm" in joined_failures and "difference" not in joined_failures and "widening" not in " ".join(logs):
        new_min = round(updated_params.get("PRIMER_MIN_TM", 57.0) + 0.5, 1)
        new_max = round(updated_params.get("PRIMER_MAX_TM", 63.0) - 0.5, 1)
        if new_min < new_max:
            logs.append("Adjusting: Tm range failed. Tightening target window by ±0.5°C.")
            updated_params["PRIMER_MIN_TM"] = new_min
            updated_params["PRIMER_MAX_TM"] = new_max

    # 5. GC Failure
    if "gc" in joined_failures and "clamp" not in joined_failures:
        logs.append("Adjusting: GC content failed. Narrowing target GC range to 45–55%.")
        updated_params["PRIMER_MIN_GC"] = 45.0
        updated_params["PRIMER_MAX_GC"] = 55.0

    # 6. Off-targets Failure
    if "blast" in joined_failures or "off-target" in joined_failures:
        logs.append("Adjusting: Off-target hits detected. Tightening 3'-end specificity constraints.")
        min_end = PARAMETER_BOUNDS.get("self_end_th_min", 15.0)
        updated_params["PRIMER_MAX_SELF_END_TH"] = max(min_end, updated_params.get("PRIMER_MAX_SELF_END_TH", 35.0) - 5.0)

    # 7. Hairpin Failure
    if "hairpin" in joined_failures:
        logs.append("Adjusting: Hairpin structure unstable. Reducing PRIMER_MAX_HAIRPIN_TH by 5.0.")
        min_hp = PARAMETER_BOUNDS.get("hairpin_th_min", 20.0)
        updated_params["PRIMER_MAX_HAIRPIN_TH"] = max(min_hp, updated_params.get("PRIMER_MAX_HAIRPIN_TH", 40.0) - 5.0)

    # 8. Dimer Failure
    if "dimer" in joined_failures:
        logs.append("Adjusting: Dimer interaction detected. Tightening 3'-end stability constraints.")
        min_end = PARAMETER_BOUNDS.get("self_end_th_min", 15.0)
        updated_params["PRIMER_MAX_SELF_END_TH"] = max(min_end, updated_params.get("PRIMER_MAX_SELF_END_TH", 35.0) - 5.0)

    # Fallback tweak
    if not logs:
        logs.append("Adjusting: Validation below threshold. Tightening primer length & Tm parameters.")
        updated_params["PRIMER_OPT_SIZE"] = 21
        updated_params["PRIMER_MIN_TM"] = 58.0
        updated_params["PRIMER_MAX_TM"] = 62.0

    return updated_params, logs


def _adjust_parameters_llm(
    failures: List[str],
    current_params: Dict[str, Any],
    gemini_client: Any,
    application: str = "Standard PCR",
) -> Tuple[Dict[str, Any], List[str]]:
    """Use Gemini to optimize parameters based on failure reasons."""
    if not gemini_client or not gemini_client.api_key:
        return _adjust_parameters_impl(failures, current_params)

    prompt = f"""As an expert molecular biologist, analyze these primer validation failures (including In-Silico PCR gate failures) and optimize design parameters:

Target Application: {application}

Current Parameters:
{json.dumps(current_params, indent=2)}

Validation Failures:
{json.dumps(failures, indent=2)}

Provide your optimization as JSON:
- updated_params: dict containing modified parameter keys and values.
- adjustments_made: list of strings with biological justifications.

Respond ONLY with valid JSON."""

    try:
        response_text = gemini_client.invoke(
            prompt=prompt,
            system_prompt="You are an expert bioinformatician optimizing PCR primer design.",
        )
        llm_result = gemini_client.extract_json(response_text)

        llm_updated_params = llm_result.get("updated_params", {})
        adjustments = llm_result.get("adjustments_made", [])

        new_params = dict(current_params)
        for k, v in llm_updated_params.items():
            if k in current_params:
                expected_type = type(current_params[k])
                try:
                    new_params[k] = expected_type(v)
                except (ValueError, TypeError):
                    new_params[k] = v
            else:
                new_params[k] = v

        if not adjustments:
            adjustments = ["Gemini adjusted parameters based on validation failures."]

        return new_params, adjustments

    except Exception as e:
        logger.warning(f"LLM parameter adjustment failed: {e}. Falling back to rule-based adjuster.")
        return _adjust_parameters_impl(failures, current_params)


@tool
def adjust_params(
    failures_json: str,
    current_params_json: str,
) -> str:
    """Adjust Primer-BLAST parameters based on specific primer evaluation failures.
    
    Use this tool when a primer design fails quality thresholds or Gate 2 In-Silico PCR.
    
    Args:
        failures_json: JSON string of failure reason list.
        current_params_json: JSON string of current parameter dictionary.
    
    Returns:
        JSON string with updated parameters and adjustment explanations.
    """
    try:
        failures = json.loads(failures_json)
    except (json.JSONDecodeError, TypeError):
        failures = [str(failures_json)]

    try:
        current_params = json.loads(current_params_json)
    except (json.JSONDecodeError, TypeError):
        current_params = {}

    updated_params, logs = _adjust_parameters_impl(failures, current_params)

    return json.dumps({
        "updated_params": updated_params,
        "adjustments_made": logs,
        "num_adjustments": len(logs),
    }, indent=2)
