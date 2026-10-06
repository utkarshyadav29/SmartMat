"""
llm_enrichment.py
Layer 2 of SmartMat Hybrid Agent.
Calls Llama-3.3-70B via Cirrascale API for strategic AI insights, global automotive trends,
and risk considerations beyond verified CSV dataset records.
"""

import json
import os
import re
from typing import Dict, Any, Optional
import requests
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("127be68f-a5cb-4714-a2f8-ed4f63ce8990")
API_BASE_URL = os.getenv("API_BASE_URL", "https://aisuite.cirrascale.com/apis/v2")
MODEL_NAME = "Llama-3.3-70B"


def _clean_and_parse_llm_output(raw_text: str) -> Dict[str, Any]:
    """
    Parses LLM output into a dictionary with required fields.
    Handles standard JSON with code fences, as well as structured key-value lines.
    """
    if not raw_text or not raw_text.strip():
        raise ValueError("Empty LLM output")

    cleaned = raw_text.strip()
    # Remove markdown code fences
    cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\s*```$", "", cleaned)

    # 1. Try standard JSON parse on outer { ... }
    match = re.search(r"\{.*\}", cleaned, flags=re.DOTALL)
    if match:
        try:
            parsed = json.loads(match.group(0).strip())
            if isinstance(parsed, dict) and any(k in parsed for k in ["global_oem_usage", "why_preferred"]):
                return parsed
        except json.JSONDecodeError:
            pass

    # 2. Try direct json.loads on cleaned text
    try:
        parsed = json.loads(cleaned)
        if isinstance(parsed, dict):
            return parsed
    except json.JSONDecodeError:
        pass

    # 3. Fallback to line-by-line key: value parsing
    parsed_lines: Dict[str, str] = {}
    current_key = None
    target_keys = ["global_oem_usage", "recent_trend", "why_preferred", "alternative_risk", "confidence"]

    for line in cleaned.splitlines():
        line_str = line.strip()
        if not line_str:
            continue

        matched_key = None
        for k in target_keys:
            pattern = rf"^[\"']?{k}[\"']?\s*:\s*(.*)"
            m = re.match(pattern, line_str, flags=re.IGNORECASE)
            if m:
                matched_key = k
                val = m.group(1).strip().strip('"').strip("'").rstrip(",")
                parsed_lines[k] = val
                break

        if matched_key:
            current_key = matched_key
        elif current_key and current_key in parsed_lines:
            # Multi-line continuation
            parsed_lines[current_key] += " " + line_str.strip('"').strip("'").rstrip(",")

    if parsed_lines and any(k in parsed_lines for k in ["global_oem_usage", "why_preferred"]):
        return parsed_lines

    raise ValueError(f"Unparseable LLM output: {raw_text[:100]}")


def fetch_llm_insights(
    material_key: str,
    component: str,
    verified_data: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Enriches verified material data with forward-looking industry insights using Llama-3.3-70B.

    Args:
        material_key: Material designation / key.
        component: Automotive target component.
        verified_data: Verified facts already retrieved from Layer 1.

    Returns:
        dict containing global_oem_usage, recent_trend, why_preferred, alternative_risk, confidence.
    """
    verified_data = verified_data or {}
    known_companies = verified_data.get("companies", "N/A")
    known_components = verified_data.get("components", "N/A")
    known_risk = verified_data.get("procurement_risk", "Unknown")

    prompt = f"""You are an automotive materials engineering and supply-chain expert.
We have verified facts from our database for material '{material_key}' in automotive application '{component}':
- Verified OEMs: {known_companies}
- Typical components: {known_components}
- Procurement risk: {known_risk}

Do NOT repeat these verified facts. Provide NEW forward-looking automotive intelligence specifically for '{component}'.

Provide your response with these exact 5 fields:
global_oem_usage: Global OEMs outside India utilizing this grade or direct equivalent
recent_trend: Latest lightweighting, EV battery casing, or circularity trends (2023-2026)
why_preferred: Primary metallurgical or manufacturing reason engineers select this for {component}
alternative_risk: Key risk if substituting with cheaper or alternative materials
confidence: high / medium / low
"""

    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json",
    }

    payload = {
        "model": MODEL_NAME,
        "messages": [
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.1,
        "max_tokens": 300,
    }

    try:
        response = requests.post(
            f"{API_BASE_URL}/chat/completions",
            headers=headers,
            json=payload,
            timeout=15,
        )

        if response.status_code != 200:
            return {
                "global_oem_usage": "API connection error",
                "recent_trend": "Service temporarily unavailable",
                "why_preferred": f"HTTP status {response.status_code}",
                "alternative_risk": "Unable to verify via LLM",
                "confidence": "low",
                "note": f"API returned non-200 code: {response.status_code}",
            }

        data = response.json()
        choice = data["choices"][0]
        raw_content = choice["message"].get("content", "")

        # In case the model routed to function calling arguments
        if not raw_content and "tool_calls" in choice["message"]:
            args = choice["message"]["tool_calls"][0].get("function", {}).get("arguments", "")
            raw_content = args

        parsed = _clean_and_parse_llm_output(raw_content)

        return {
            "global_oem_usage": str(parsed.get("global_oem_usage", "Adopted across global automotive platforms")),
            "recent_trend": str(parsed.get("recent_trend", "Focus on recycled content integration and lightweighting")),
            "why_preferred": str(parsed.get("why_preferred", f"Proven balance of properties for {component}")),
            "alternative_risk": str(parsed.get("alternative_risk", "Potential fatigue or formability compromise")),
            "confidence": str(parsed.get("confidence", "medium")).lower(),
        }

    except Exception as e:
        return {
            "global_oem_usage": "Fallback estimate: standard industry application",
            "recent_trend": "Increasing sustainability and lightweighting focus",
            "why_preferred": f"Selected for strength/weight profile in {component}",
            "alternative_risk": "Manufacturing and thermal tolerance considerations",
            "confidence": "low",
            "note": f"LLM enrichment fallback: {str(e)}",
        }


if __name__ == "__main__":
    test_key = "ANSI Steel SAE 1015 as-rolled"
    test_comp = "Chassis"
    dummy_verified = {
        "companies": "Mahindra Accelo; BMW Group",
        "components": "Body-in-White, chassis components",
        "procurement_risk": "Low",
    }
    print(f"Fetching LLM insights for '{test_key}' in '{test_comp}'...")
    insights = fetch_llm_insights(test_key, test_comp, dummy_verified)
    print(json.dumps(insights, indent=2))
