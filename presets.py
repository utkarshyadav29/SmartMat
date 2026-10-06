"""
presets.py
Default slider values for automobile components and sustainability filter presets.
Used by app.py and api.py for component-based weight presets and filtering.
"""

COMPONENT_PRESETS = {
    "Chassis / Frame": {
        "strength": 9,
        "weight": 7,
        "cost": 7,
        "temp": 7,
        "sustainability": 5,
    },
    "Body Panel / Skin": {
        "strength": 7,
        "weight": 9,
        "cost": 8,
        "temp": 5,
        "sustainability": 6,
    },
    "Engine Block": {
        "strength": 8,
        "weight": 5,
        "cost": 6,
        "temp": 9,
        "sustainability": 4,
    },
    "Suspension Component": {
        "strength": 9,
        "weight": 7,
        "cost": 7,
        "temp": 7,
        "sustainability": 5,
    },
    "Brake System": {
        "strength": 8,
        "weight": 6,
        "cost": 7,
        "temp": 9,
        "sustainability": 5,
    },
    "Wheel / Rim": {
        "strength": 7,
        "weight": 8,
        "cost": 7,
        "temp": 6,
        "sustainability": 6,
    },
    "Interior Structure": {
        "strength": 5,
        "weight": 8,
        "cost": 9,
        "temp": 4,
        "sustainability": 7,
    },
    "Exhaust System": {
        "strength": 7,
        "weight": 6,
        "cost": 6,
        "temp": 9,
        "sustainability": 4,
    },
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
