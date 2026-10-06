"""
merge_datasets.py
SmartMat — One-time dataset merge script
Run this ONCE before anything else.
Creates SmartMat_Master.csv used by all other scripts.

Run: python merge_datasets.py
"""

import pandas as pd
from pathlib import Path

BASE = Path(__file__).resolve().parent

def merge_all():
    print("Loading source files...")

    main = pd.read_csv(BASE / "Main_SmartMat.csv")
    ev   = pd.read_csv(BASE / "Material_Industry_Evidence.csv")
    mk   = pd.read_csv(BASE / "Material_Market_Availability.csv")

    print(f"  Main_SmartMat:              {main.shape}")
    print(f"  Material_Industry_Evidence: {ev.shape}")
    print(f"  Material_Market_Availability: {mk.shape}")

    # Deduplicate evidence and market on Material_Key
    # 92 materials share names — keep first occurrence
    ev_clean = ev.drop_duplicates(subset="Material_Key", keep="first")
    mk_clean = mk.drop_duplicates(subset="Material_Key", keep="first")

    print("\nDeduplication done.")
    print(f"  Evidence after dedup: {ev_clean.shape}")
    print(f"  Market after dedup:   {mk_clean.shape}")

    # Left join — keep all 1552 from main
    merged = main.merge(ev_clean, on="Material_Key", how="left")
    merged = merged.merge(mk_clean, on="Material_Key",
                          how="left", suffixes=("", "_mkt"))

    # Drop duplicate Material_Family column from market file
    merged = merged.drop(columns=["Material_Family_mkt"], errors="ignore")

    print(f"\nMerged shape: {merged.shape}")
    print(f"Total columns: {len(merged.columns)}")

    # Verify no nulls in critical columns
    critical = [
        "Ultimate_Strength_MPa",
        "Density_kg_m3",
        "Material_Cost_INR_per_kg",
        "Embodied_Carbon_kgCO2e_per_kg",
        "Strength_to_Weight_Index",
        "Strength_to_Cost_MPa_per_INRkg",
        "India_Availability",
        "Procurement_Risk",
        "Industry_Examples",
        "Evidence_Source",
    ]
    print("\nNull check on critical columns:")
    for col in critical:
        nulls = merged[col].isnull().sum()
        status = "[OK]" if nulls == 0 else f"[WARN] {nulls} nulls"
        print(f"  {col}: {status}")

    # Save master file
    out = BASE / "SmartMat_Master.csv"
    merged.to_csv(out, index=False)
    print(f"\n[OK] SmartMat_Master.csv saved -> {out}")
    print(f"   Rows: {len(merged)} | Columns: {len(merged.columns)}")
    return merged

if __name__ == "__main__":
    merge_all()