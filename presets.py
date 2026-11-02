"""
presets.py
Default slider values for automobile components and sustainability filter presets.
Used by app.py and api.py for component-based weight presets and filtering.
"""

COMPONENT_PRESETS = {

    "Chassis / Frame": {
        "strength": 9,
        "weight": 8,
        "cost": 6,
        "temp": 3,
        "sustainability": 7,

        "priority": "structural",
        "min_strength_score": 5.0,
        "min_temp_score": 2.0,
        "evidence_keywords": [
            "chassis",
            "frame",
            "structural"
        ]
    },

    "Body Panel / Skin": {
        "strength": 5,
        "weight": 10,
        "cost": 7,
        "temp": 2,
        "sustainability": 8,

        "priority": "lightweight_formability",
        "min_strength_score": 3.0,
        "min_temp_score": 1.0,
        "evidence_keywords": [
            "body",
            "panel",
            "sheet",
            "skin",
            "stamping"
        ]
    },

    "Engine Block": {
        "strength": 8,
        "weight": 6,
        "cost": 6,
        "temp": 10,
        "sustainability": 5,

        "priority": "thermal_structural",
        "min_strength_score": 6.0,
        "min_temp_score": 7.0,
        "evidence_keywords": [
            "engine",
            "block",
            "cylinder",
            "powertrain"
        ]
    },

    "Suspension Component": {
        "strength": 10,
        "weight": 7,
        "cost": 5,
        "temp": 3,
        "sustainability": 6,

        "priority": "fatigue_structural",
        "min_strength_score": 7.0,
        "min_temp_score": 1.0,
        "evidence_keywords": [
            "suspension",
            "spring",
            "control arm",
            "link",
            "steering"
        ]
    },

    "Brake System": {
        "strength": 8,
        "weight": 6,
        "cost": 5,
        "temp": 10,
        "sustainability": 6,

        "priority": "thermal_wear",
        "min_strength_score": 6.0,
        "min_temp_score": 7.0,
        "evidence_keywords": [
            "brake",
            "rotor",
            "disc",
            "caliper"
        ]
    },

    "Wheel / Rim": {
        "strength": 8,
        "weight": 9,
        "cost": 6,
        "temp": 3,
        "sustainability": 7,

        "priority": "lightweight_fatigue",
        "min_strength_score": 6.0,
        "min_temp_score": 1.0,
        "evidence_keywords": [
            "wheel",
            "rim"
        ]
    },

    "Interior Structure": {
        "strength": 5,
        "weight": 9,
        "cost": 7,
        "temp": 3,
        "sustainability": 9,

        "priority": "lightweight_sustainable",
        "min_strength_score": 3.0,
        "min_temp_score": 1.0,
        "evidence_keywords": [
            "interior",
            "seat",
            "dashboard",
            "trim",
            "cockpit"
        ]
    },

    "Exhaust System": {
        "strength": 8,
        "weight": 7,
        "cost": 5,
        "temp": 10,
        "sustainability": 8,

        "priority": "high_temperature",
        "min_strength_score": 6.0,
        "min_temp_score": 7.0,
        "evidence_keywords": [
            "exhaust",
            "thermal",
            "manifold",
            "header",
            "muffler",
            "downpipe",
            "heat shield"
        ]
    }
}
# Standard aliases for short forms
COMPONENT_PRESETS["Chassis"] = COMPONENT_PRESETS["Chassis / Frame"]
COMPONENT_PRESETS["Body Panel"] = COMPONENT_PRESETS["Body Panel / Skin"]
COMPONENT_PRESETS["Suspension"] = COMPONENT_PRESETS["Suspension Component"]
COMPONENT_PRESETS["Wheel/Rim"] = COMPONENT_PRESETS["Wheel / Rim"]
COMPONENT_PRESETS["Interior"] = COMPONENT_PRESETS["Interior Structure"]

SUSTAINABILITY_FILTERS = {
    "must_recycle": {
        "label": "High Recyclability",
        "description": "Established recycling infrastructure (Aluminum, Steel, standard structural alloys)",
        "filter_description": "Filters for metals and high-recyclability materials (excluding hard-to-recycle blends)",
    },
    "low_carbon": {
        "label": "Low Embodied Carbon",
        "description": "Embodied carbon emissions <= 5.0 kgCO2e/kg",
        "filter_description": "Embodied_Carbon_kgCO2e_per_kg <= 5.0",
    },
    "eco_label": {
        "label": "Eco-Friendly Rated",
        "description": "Materials evaluated as Eco-Friendly (sustainability_score >= 6.5)",
        "filter_description": "sustainability_score >= 6.5 or recommendation == 'Eco-Friendly Material'",
    },
    "bio_based": {
        "label": "Bio-Based / Renewable",
        "description": "Bio-derived polymers or natural composites",
        "filter_description": "Keyword search for bio/natural composite materials in Family or Key",
    },
}
