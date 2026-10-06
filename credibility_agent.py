"""
credibility_agent.py
Layer 1 of SmartMat Hybrid Agent.
Pure CSV lookup with zero LLM hallucination risk.
Queries SmartMat_Master.csv for verified OEM evidence, application history, and supply chain availability.
"""

from pathlib import Path
from typing import Dict, Any, Optional
import pandas as pd

_CACHED_MASTER_DF: Optional[pd.DataFrame] = None
BASE_DIR = Path(__file__).resolve().parent


def get_master_data() -> pd.DataFrame:
    """Load and cache SmartMat_Master.csv so it is not reloaded on every call."""
    global _CACHED_MASTER_DF
    if _CACHED_MASTER_DF is None:
        csv_path = BASE_DIR / "SmartMat_Master.csv"
        if not csv_path.exists():
            raise FileNotFoundError(f"SmartMat_Master.csv not found at: {csv_path}")
        _CACHED_MASTER_DF = pd.read_csv(csv_path)
    return _CACHED_MASTER_DF


def fetch_verified_credibility(material_key: str) -> Dict[str, Any]:
    """
    Looks up verified industry evidence and supply chain data from SmartMat_Master.csv.

    Args:
        material_key: Identifier or designation of the material.

    Returns:
        dict containing verified industry evidence, availability, and found status.
    """
    df = get_master_data()
    mat_str = str(material_key).strip()

    # 1. Exact match
    match = df[df["Material_Key"] == mat_str]

    # 2. Case-insensitive exact match fallback
    if match.empty:
        match = df[df["Material_Key"].str.strip().str.lower() == mat_str.lower()]

    # 3. Case-insensitive substring match fallback
    if match.empty:
        match = df[df["Material_Key"].str.lower().str.contains(mat_str.lower(), regex=False, na=False)]

    # 4. Reverse substring match fallback
    if match.empty:
        match = df[df["Material_Key"].apply(lambda k: str(k).lower() in mat_str.lower())]

    if match.empty:
        return {
            "material_key": material_key,
            "companies": "No verified OEM records found",
            "components": "N/A",
            "application": "N/A",
            "evidence_level": "None",
            "evidence_status": "Unverified",
            "source": "None",
            "india_availability": "Unknown",
            "global_availability": "Unknown",
            "procurement_risk": "Unknown",
            "supplier_info": "N/A",
            "market_source": "None",
            "found": False,
        }

    row = match.iloc[0]

    def _val(col_name: str, default: str = "N/A") -> str:
        if col_name in row and pd.notna(row[col_name]):
            return str(row[col_name]).strip()
        return default

    return {
        "material_key": _val("Material_Key", mat_str),
        "companies": _val("Industry_Examples"),
        "components": _val("Common_Components"),
        "application": _val("Common_Automotive_Applications"),
        "evidence_level": _val("Industry_Evidence_Level"),
        "evidence_status": _val("Evidence_Status"),
        "source": _val("Evidence_Source"),
        "india_availability": _val("India_Availability"),
        "global_availability": _val("Global_Availability"),
        "procurement_risk": _val("Procurement_Risk"),
        "supplier_info": _val("Supplier_Information"),
        "market_source": _val("Market_Source"),
        "found": True,
    }


if __name__ == "__main__":
    test_key = "ANSI Steel SAE 1015 as-rolled"
    print(f"Fetching credibility for '{test_key}':")
    res = fetch_verified_credibility(test_key)
    for k, v in res.items():
        print(f"  {k}: {v}")
