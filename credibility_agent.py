"""
credibility_agent.py

Evidence and credibility lookup for SmartMat.

Rules:
- This module ONLY reports what exists in SmartMat_Master.csv.
- Missing evidence is never upgraded to verified evidence.
- No OEM/company names are invented.
- Credibility is separate from engineering suitability.
"""

from pathlib import Path
from typing import Dict, Any, Optional

import pandas as pd


_CACHED_MASTER_DF: Optional[pd.DataFrame] = None

BASE_DIR = Path(__file__).resolve().parent


def get_master_data() -> pd.DataFrame:
    """Load and cache SmartMat_Master.csv."""

    global _CACHED_MASTER_DF

    if _CACHED_MASTER_DF is None:

        csv_path = BASE_DIR / "SmartMat_Master.csv"

        if not csv_path.exists():
            raise FileNotFoundError(
                f"SmartMat_Master.csv not found at: {csv_path}"
            )

        _CACHED_MASTER_DF = pd.read_csv(csv_path)

    return _CACHED_MASTER_DF


def _clean(value: Any, default: str = "Unknown") -> str:
    """Convert CSV values to safe display strings."""

    if value is None:
        return default

    if pd.isna(value):
        return default

    text = str(value).strip()

    if not text:
        return default

    if text.lower() in {
        "nan",
        "none",
        "null",
        "n/a",
        "na",
    }:
        return default

    return text


def _find_material(
    df: pd.DataFrame,
    material_key: str,
) -> pd.DataFrame:

    mat_str = str(material_key).strip()

    if "Material_Key" not in df.columns:
        return pd.DataFrame()

    # 1. Exact match
    match = df[
        df["Material_Key"].astype(str).str.strip()
        == mat_str
    ]

    if not match.empty:
        return match

    # 2. Case-insensitive exact match
    match = df[
        df["Material_Key"]
        .astype(str)
        .str.strip()
        .str.lower()
        == mat_str.lower()
    ]

    if not match.empty:
        return match

    # 3. Safe substring match
    match = df[
        df["Material_Key"]
        .astype(str)
        .str.lower()
        .str.contains(
            mat_str.lower(),
            regex=False,
            na=False,
        )
    ]

    if not match.empty:
        return match

    # 4. Reverse substring match
    match = df[
        df["Material_Key"]
        .astype(str)
        .apply(
            lambda k: str(k).lower()
            in mat_str.lower()
        )
    ]

    return match


def classify_credibility(
    evidence_status: str,
    evidence_level: str,
    common_components: str,
    requested_component: str,
) -> str:
    """
    Determine evidence credibility without inventing evidence.

    HIGH:
        Verified grade/component-specific evidence.

    MEDIUM:
        Industry/application-level evidence.

    LOW:
        Evidence exists but is weak/non-specific.

    UNVERIFIED:
        No reliable evidence established.
    """

    status = str(
        evidence_status or ""
    ).strip().lower()

    level = str(
        evidence_level or ""
    ).strip().lower()

    components = str(
        common_components or ""
    ).lower()

    component = str(
        requested_component or ""
    ).lower()

    # -------------------------------------------------------------
    # Explicitly unverified
    # -------------------------------------------------------------

    if (
        not status
        or status in {
            "unknown",
            "unverified",
            "none",
            "not verified",
        }
    ):
        return "UNVERIFIED"

    # -------------------------------------------------------------
    # Grade/component-specific verified evidence
    # -------------------------------------------------------------

    exact_component_evidence = any(
        token in components
        for token in [
            component,
            "exhaust",
            "chassis",
            "frame",
            "brake",
            "wheel",
            "engine",
            "suspension",
            "body",
            "interior",
        ]
    )

    verified = (
        "verified" in status
        or "confirmed" in status
        or "grade-specific" in status
        or "oem" in level
    )

    if verified and exact_component_evidence:
        return "HIGH"

    # -------------------------------------------------------------
    # Industry/application evidence
    # -------------------------------------------------------------

    industry = (
        "industry" in status
        or "industry" in level
        or "application" in level
        or "automotive" in level
    )

    if industry and exact_component_evidence:
        return "MEDIUM"

    # -------------------------------------------------------------
    # Generic verified material information
    # -------------------------------------------------------------

    if verified:
        return "MEDIUM"

    # -------------------------------------------------------------
    # Weak evidence
    # -------------------------------------------------------------

    if (
        status
        not in {
            "",
            "unknown",
            "unverified",
            "none",
        }
    ):
        return "LOW"

    return "UNVERIFIED"


def fetch_verified_credibility(
    material_key: str,
    requested_component: str = "",
) -> Dict[str, Any]:
    """
    Look up evidence for a material.

    IMPORTANT:
    This function never creates or upgrades evidence.
    """

    df = get_master_data()

    match = _find_material(
        df,
        material_key,
    )

    # -------------------------------------------------------------
    # No material found
    # -------------------------------------------------------------

    if match.empty:

        return {
            "material_key": material_key,

            "companies": "No verified industry examples found",
            "components": "Unknown",
            "application": "Unknown",

            "evidence_level": "None",
            "evidence_status": "Unverified",
            "source": "None",

            "india_availability": "Unknown",
            "global_availability": "Unknown",
            "procurement_risk": "Unknown",

            "supplier_info": "Unknown",
            "market_source": "None",

            "credibility": "UNVERIFIED",

            "found": False,
        }

    row = match.iloc[0]

    def val(
        column: str,
        default: str = "Unknown",
    ) -> str:

        if column not in row:
            return default

        return _clean(
            row[column],
            default,
        )

    material = val(
        "Material_Key",
        str(material_key),
    )

    companies = val(
        "Industry_Examples",
        "No verified industry examples found",
    )

    components = val(
        "Common_Components",
        "Unknown",
    )

    application = val(
        "Common_Automotive_Applications",
        "Unknown",
    )

    evidence_level = val(
        "Industry_Evidence_Level",
        "Unknown",
    )

    evidence_status = val(
        "Evidence_Status",
        "Unverified",
    )

    source = val(
        "Evidence_Source",
        "Unknown",
    )

    credibility = classify_credibility(
        evidence_status=evidence_status,
        evidence_level=evidence_level,
        common_components=components,
        requested_component=requested_component,
    )

    return {

        "material_key": material,

        "companies": companies,
        "components": components,
        "application": application,

        "evidence_level": evidence_level,
        "evidence_status": evidence_status,
        "source": source,

        "india_availability": val(
            "India_Availability"
        ),

        "global_availability": val(
            "Global_Availability"
        ),

        "procurement_risk": val(
            "Procurement_Risk"
        ),

        "supplier_info": val(
            "Supplier_Information"
        ),

        "market_source": val(
            "Market_Source"
        ),

        "credibility": credibility,

        "found": True,
    }


if __name__ == "__main__":

    test_key = (
        "ANSI Steel SAE 1015 as-rolled"
    )

    print(
        f"Fetching credibility for "
        f"'{test_key}':"
    )

    result = fetch_verified_credibility(
        test_key,
        requested_component="Exhaust System",
    )

    for key, value in result.items():
        print(
            f"  {key}: {value}"
        )