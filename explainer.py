# explainer.py

import os
from typing import List, Dict, Any, Union
import requests
from dotenv import load_dotenv

load_dotenv()

API_KEY      = os.getenv("API_KEY")
API_BASE_URL = os.getenv("API_BASE_URL", "https://aisuite.cirrascale.com/apis/v2")
MODEL_NAME   = "Llama-3.1-8B"


def get_explanation(
    top3: List[str],
    component: Union[str, float, int] = "Chassis",
    user_requirements: Union[Dict[str, Any], float, int, None] = None,
) -> str:
    """
    Generates a concise engineering comparison between the top recommended materials
    using Cirrascale Llama-3.1-8B.

    Args:
        top3: List of top recommended material names (at least 2-3).
        component: Automotive component name (e.g. 'Chassis', 'Engine Block').
        user_requirements: Dict of user requirement scores (strength, weight, cost, temp, sustainability).

    Returns:
        String explanation and comparison conclusion under 80 words.
    """
    # Backward compatibility with legacy get_explanation(top3, strength, weight)
    if isinstance(component, (int, float)) and isinstance(user_requirements, (int, float)):
        req_dict = {"strength": component, "weight": user_requirements}
        comp_str = "Automotive Component"
    else:
        comp_str = str(component) if component else "Automotive Component"
        req_dict = user_requirements if isinstance(user_requirements, dict) else {}

    str_val = req_dict.get("strength", "N/A")
    wt_val  = req_dict.get("weight", "N/A")
    cst_val = req_dict.get("cost", "N/A")
    tmp_val = req_dict.get("temp", "N/A")
    sus_val = req_dict.get("sustainability", "N/A")

    mat1 = top3[0] if len(top3) > 0 else "Primary Material"
    mat2 = top3[1] if len(top3) > 1 else "Secondary Material"
    mat3 = top3[2] if len(top3) > 2 else "Tertiary Material"

    prompt = f"""You are an automotive material selection advisor.
Application: {comp_str}
Engineering Requirements:
- Strength: {str_val}/10
- Weight Sensitivity: {wt_val}/10
- Cost Economy: {cst_val}/10
- High Temperature: {tmp_val}/10
- Sustainability: {sus_val}/10

Ranked Candidates:
1. {mat1}
2. {mat2}
3. {mat3}

Explain in simple engineering terms why #1 ({mat1}) is the best match for {comp_str} over #2 ({mat2}).
Provide a direct comparison conclusion between #1 and #2.
Keep your entire response under 80 words without jargon.
"""

    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json",
    }

    payload = {
        "model": MODEL_NAME,
        "messages": [
            {"role": "user", "content": prompt}
        ],
        "max_tokens": 150,
        "temperature": 0.2,
    }

    try:
        response = requests.post(
            f"{API_BASE_URL}/chat/completions",
            headers=headers,
            json=payload,
            timeout=15,
        )

        if response.status_code == 200:
            result = response.json()
            return result["choices"][0]["message"]["content"].strip()
        else:
            return (
                f"{mat1} provides the optimal balance of mechanical strength and component compatibility "
                f"for {comp_str}, outperforming {mat2} in specific application requirements."
            )
    except Exception as e:
        return (
            f"{mat1} is recommended as the primary choice for {comp_str} due to its balanced performance "
            f"profile, offering higher engineering margins than {mat2}."
        )


if __name__ == "__main__":
    sample_top3 = [
        "ANSI Steel SAE 5160",
        "ANSI Steel SAE 1015 as-rolled",
        "Aluminum 6061-T6",
    ]
    sample_reqs = {
        "strength": 9,
        "weight": 7,
        "cost": 7,
        "temp": 7,
        "sustainability": 5,
    }
    explanation = get_explanation(sample_top3, "Chassis", sample_reqs)
    print("Explanation:\n", explanation)