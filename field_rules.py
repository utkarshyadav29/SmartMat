"""
field_rules.py

Component-specific engineering screening rules for SmartMat.

Important:
- These are HARD screening rules.
- A failed hard requirement is not compensated by cost, weight,
  sustainability, or another criterion.
- We do NOT relax failed engineering constraints automatically.
- Application relevance is recorded separately from engineering feasibility.
"""

from typing import Dict, Any, Tuple, Optional, Union
import pandas as pd


# ---------------------------------------------------------------------
# Component engineering screening profiles
# ---------------------------------------------------------------------
#
# These thresholds are screening-level requirements for the demo.
# They are NOT certified design allowables.
#
# Only properties actually available in SmartMat_Master.csv should be
# used here.
#
COMPONENT_RULES: Dict[str, Dict[str, Any]] = {

    "Chassis / Frame": {
        "minimum_ultimate_strength_mpa": 400.0,
        "application_keywords": [
            "chassis",
            "frame",
            "structural",
        ],
    },

    "Body Panel / Skin": {
        "minimum_ultimate_strength_mpa": 250.0,
        "application_keywords": [
            "body",
            "panel",
            "sheet",
            "skin",
            "body-in-white",
        ],
    },

    "Engine Block": {
        "minimum_ultimate_strength_mpa": 200.0,
        "minimum_service_temperature_c": 200.0,
        "application_keywords": [
            "engine",
            "block",
            "cylinder",
            "powertrain",
        ],
    },

    "Suspension Component": {
        "minimum_ultimate_strength_mpa": 500.0,
        "application_keywords": [
            "suspension",
            "spring",
            "control arm",
            "link",
            "steering",
        ],
    },

    "Brake System": {
        "minimum_ultimate_strength_mpa": 300.0,
        "minimum_service_temperature_c": 300.0,
        "application_keywords": [
            "brake",
            "rotor",
            "disc",
            "caliper",
        ],
    },

    "Wheel / Rim": {
        "minimum_ultimate_strength_mpa": 300.0,
        "application_keywords": [
            "wheel",
            "rim",
        ],
    },

    "Interior Structure": {
        "minimum_ultimate_strength_mpa": 150.0,
        "application_keywords": [
            "interior",
            "seat",
            "dashboard",
            "trim",
            "cockpit",
        ],
    },

    "Exhaust System": {
        "minimum_ultimate_strength_mpa": 300.0,
        "minimum_service_temperature_c": 500.0,
        "application_keywords": [
            "exhaust",
            "thermal",
            "manifold",
            "header",
            "muffler",
            "downpipe",
            "heat shield",
        ],
    },
}


# ---------------------------------------------------------------------
# Component name aliases
# ---------------------------------------------------------------------

_COMPONENT_ALIASES = {
    "chassis": "Chassis / Frame",
    "frame": "Chassis / Frame",

    "body panel": "Body Panel / Skin",
    "body": "Body Panel / Skin",
    "body panel / skin": "Body Panel / Skin",

    "engine": "Engine Block",
    "engine block": "Engine Block",

    "suspension": "Suspension Component",
    "suspension component": "Suspension Component",

    "brake": "Brake System",
    "brake system": "Brake System",

    "wheel": "Wheel / Rim",
    "rim": "Wheel / Rim",
    "wheel/rim": "Wheel / Rim",
    "wheel / rim": "Wheel / Rim",

    "interior": "Interior Structure",
    "interior structure": "Interior Structure",

    "exhaust": "Exhaust System",
    "exhaust system": "Exhaust System",
}


def _resolve_component(component: str) -> Optional[str]:
    """Resolve UI component names to the canonical component profile."""

    if not component:
        return None

    text = str(component).strip()

    if text in COMPONENT_RULES:
        return text

    lowered = text.lower()

    if lowered in _COMPONENT_ALIASES:
        return _COMPONENT_ALIASES[lowered]

    for alias, canonical in _COMPONENT_ALIASES.items():
        if alias in lowered:
            return canonical

    return None


def _contains_any(value: Any, keywords: list[str]) -> bool:
    """Return True if any application keyword appears in the value."""

    text = str(value).lower()

    return any(
        keyword.lower() in text
        for keyword in keywords
    )


def _application_relevance(
    row: pd.Series,
    keywords: list[str],
) -> str:
    """
    Classify application evidence.

    HIGH:
        Explicit component/application match.

    MEDIUM:
        Material has automotive application information but no explicit
        component match.

    LOW:
        No relevant application evidence established.
    """

    components = str(
        row.get("Common_Components", "")
    ).lower()

    applications = str(
        row.get("Common_Automotive_Applications", "")
    ).lower()

    combined = f"{components} {applications}"

    if any(
        keyword.lower() in combined
        for keyword in keywords
    ):
        return "HIGH"

    if applications.strip() and applications.lower() not in {
        "nan",
        "n/a",
        "unknown",
    }:
        return "MEDIUM"

    return "LOW"


def apply_field_rules(
    df: pd.DataFrame,
    component: str,
    return_note: bool = False,
) -> Union[
    pd.DataFrame,
    Tuple[pd.DataFrame, Optional[str]]
]:
    """
    Apply component-specific hard engineering screening rules.

    IMPORTANT:
    Failed hard constraints are NOT relaxed automatically.

    Application relevance is added as:
        _application_relevance

    Possible values:
        HIGH
        MEDIUM
        LOW

    This application relevance is evidence metadata. It should not be
    confused with engineering feasibility.
    """

    if df.empty:
        note = "Input dataframe is empty."

        if return_note:
            return df.copy(), note

        result = df.copy()
        result.attrs["rules_note"] = note
        return result

    canonical = _resolve_component(component)

    if canonical is None:
        result = df.copy()

        result["_application_relevance"] = "LOW"

        note = (
            f"No component-specific hard rules found for "
            f"'{component}'. Dataset retained for screening."
        )

        result.attrs["rules_note"] = note

        if return_note:
            return result, note

        return result

    profile = COMPONENT_RULES[canonical]

    mask = pd.Series(
        True,
        index=df.index,
        dtype=bool,
    )

    applied_rules = []

    # -------------------------------------------------------------
    # Ultimate strength
    # -------------------------------------------------------------

    min_uts = profile.get(
        "minimum_ultimate_strength_mpa"
    )

    if min_uts is not None:

        if "Ultimate_Strength_MPa" in df.columns:

            values = pd.to_numeric(
                df["Ultimate_Strength_MPa"],
                errors="coerce",
            )

            mask &= values >= float(min_uts)

            applied_rules.append(
                f"Ultimate_Strength_MPa >= {min_uts} MPa"
            )

    # -------------------------------------------------------------
    # Service temperature
    # -------------------------------------------------------------

    min_temp = profile.get(
        "minimum_service_temperature_c"
    )

    if min_temp is not None:

        if "Max_Service_Temperature_C" in df.columns:

            values = pd.to_numeric(
                df["Max_Service_Temperature_C"],
                errors="coerce",
            )

            mask &= values >= float(min_temp)

            applied_rules.append(
                f"Max_Service_Temperature_C >= {min_temp} °C"
            )

    filtered = df.loc[mask].copy()

    # -------------------------------------------------------------
    # Application relevance
    # -------------------------------------------------------------

    keywords = profile.get(
        "application_keywords",
        [],
    )

    filtered["_application_relevance"] = filtered.apply(
        lambda row: _application_relevance(
            row,
            keywords,
        ),
        axis=1,
    )

    # -------------------------------------------------------------
    # Note
    # -------------------------------------------------------------

    note = (
        f"{canonical}: "
        f"applied hard engineering rules "
        f"{applied_rules if applied_rules else 'none'}. "
        f"{len(filtered)} of {len(df)} materials passed."
    )

    filtered.attrs["rules_note"] = note

    if return_note:
        return filtered, note

    return filtered


def apply_field_rules_with_note(
    df: pd.DataFrame,
    component: str,
) -> Tuple[pd.DataFrame, Optional[str]]:
    """Explicit tuple-returning convenience wrapper."""

    return apply_field_rules(
        df,
        component,
        return_note=True,
    )


if __name__ == "__main__":

    test_df = pd.DataFrame({

        "Material_Key": [
            "Mat A",
            "Mat B",
            "Mat C",
        ],

        "Ultimate_Strength_MPa": [
            600,
            350,
            180,
        ],

        "Max_Service_Temperature_C": [
            700,
            250,
            150,
        ],

        "Common_Components": [
            "Exhaust / thermal components",
            "Chassis / structural",
            "Interior structure",
        ],

        "Common_Automotive_Applications": [
            "Exhaust system",
            "Automotive chassis",
            "Interior",
        ],
    })

    for component in [
        "Chassis / Frame",
        "Body Panel / Skin",
        "Engine Block",
        "Suspension Component",
        "Brake System",
        "Wheel / Rim",
        "Interior Structure",
        "Exhaust System",
    ]:

        result, note = apply_field_rules_with_note(
            test_df,
            component,
        )

        print(
            f"\n{component}"
        )
        print(note)

        if not result.empty:
            print(
                result[
                    [
                        "Material_Key",
                        "_application_relevance",
                    ]
                ].to_string(index=False)
            )