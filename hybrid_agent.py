"""
hybrid_agent.py
SmartMat Hybrid Credibility Agent Orchestrator.
Combines:
  Layer 1: Deterministic CSV verification from SmartMat_Master.csv (High Trust)
  Layer 2: Generative strategic intelligence from Llama-3.3-70B (Medium Trust)
Maintains strict data separation with clear provenance labelling.
"""

from typing import Dict, Any
import json
from credibility_agent import fetch_verified_credibility
from llm_enrichment import fetch_llm_insights


def get_hybrid_credibility(material_key: str, component: str = "Chassis") -> Dict[str, Any]:
    """
    Orchestrates Layer 1 (CSV verification) and Layer 2 (LLM 70B enrichment).

    Args:
        material_key: Material designation key.
        component: Automotive component context.

    Returns:
        dict containing separated verified_data, ai_insights, material, and component.
    """
    # Step 1: Fetch deterministic ground truth from CSV
    verified_data = fetch_verified_credibility(material_key)

    # Step 2: Fetch forward-looking strategic AI insights
    ai_insights = fetch_llm_insights(material_key, component, verified_data=verified_data)

    # Step 3: Return merged result with strict provenance separation
    return {
        "material": material_key,
        "component": component,
        "verified_data": verified_data,
        "ai_insights": ai_insights,
        "provenance": {
            "verified_data": "High Trust (SmartMat_Master.csv OEM & Industry Ground Truth)",
            "ai_insights": "Medium Trust (Cirrascale Llama-3.3-70B Engineering Analysis)",
        },
    }


if __name__ == "__main__":
    test_mat = "ANSI Steel SAE 1015 as-rolled"
    test_comp = "Chassis"
    print(f"Executing Hybrid Credibility Agent for '{test_mat}' in '{test_comp}'...\n")
    result = get_hybrid_credibility(test_mat, test_comp)
    print(json.dumps(result, indent=2))
