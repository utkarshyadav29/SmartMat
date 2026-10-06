"""
app.py

SmartMat Demo Application built with Streamlit.
Allows users to specify required strength and weight sensitivity to receive
intelligent material category recommendations powered by Decision Tree ML.
"""
from pathlib import Path
import pickle
import pandas as pd
import streamlit as st
from explainer import get_explanation

# Application Title
st.title("SmartMat Demo")
st.write("Find the optimal material category for your engineering requirements based on strength and weight sensitivity.")

# User Inputs: Sliders
strength_required = st.slider(
    "Strength Required",
    min_value=1.0,
    max_value=10.0,
    value=5.0,
    step=0.1,
    help="1 = Minimal strength needed, 10 = Maximum tensile strength required.",
)

weight_sensitivity = st.slider(
    "Weight Sensitivity",
    min_value=1.0,
    max_value=10.0,
    value=5.0,
    step=0.1,
    help="1 = Heavy materials acceptable, 10 = Ultra-lightweight critical.",
)

# Action Button
if st.button("Find Material"):
    model_path = Path(__file__).resolve().parent / "model.pkl"

    if not model_path.exists():
        st.error("`model.pkl` not found! Please run `python model.py` to train and save the model first.")
    else:
        # Load trained Decision Tree model
        with open(model_path, "rb") as f:
            model = pickle.load(f)

        # Prepare input features matching training column names
        input_data = pd.DataFrame(
            [[strength_required, weight_sensitivity]],
            columns=["strength_score", "weight_score"],
        )

        # Run prediction
        prediction = model.predict(input_data)[0]

        # Display result category
        st.success(f"**Recommendation:** {prediction}")

        # Show matching candidate materials if scored dataset is available
        data_path = Path(__file__).resolve().parent / "materials_scored.csv"
        if data_path.exists():
            df = pd.read_csv(data_path)

            # Check if prediction corresponds to recommendation bucket or material name
            if "recommendation" in df.columns and prediction in df["recommendation"].values:
                matching_rows = df[df["recommendation"] == prediction].copy()
                st.subheader(f"Top Materials in '{prediction}'")

                # Rank by proximity to chosen slider criteria
                matching_rows["distance"] = (
                    (matching_rows["strength_score"] - strength_required) ** 2
                    + (matching_rows["weight_score"] - weight_sensitivity) ** 2
                )
                top_candidates = matching_rows.sort_values("distance").head(5)

                display_cols = [
                    "Material",
                    "Su",
                    "strength_score",
                    "Ro",
                    "weight_score",
                    "cost_score",
                    "sustainability_score",
                ]
                existing_display = [c for c in display_cols if c in top_candidates.columns]
                st.dataframe(top_candidates[existing_display].reset_index(drop=True))

                # AI Explanation for top recommended materials
                top3_names = top_candidates.head(3)["Material"].tolist()
                if top3_names:
                    with st.spinner("Getting AI explanation..."):
                        try:
                            explanation = get_explanation(top3_names, strength_required, weight_sensitivity)
                            st.subheader("AI Analysis")
                            st.info(explanation)
                        except Exception as e:
                            st.warning(f"Could not load AI explanation: {e}")

            elif "Material" in df.columns and prediction in df["Material"].values:
                matching_rows = df[df["Material"] == prediction]
                st.subheader("Material Specifications")
                sample = matching_rows.iloc[0]

                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Tensile Strength (Su)", f"{sample.get('Su', 'N/A')} MPa")
                    st.metric("Strength Score", f"{sample.get('strength_score', 'N/A')} / 10")
                with col2:
                    st.metric("Density (Ro)", f"{sample.get('Ro', 'N/A')} kg/m³")
                    st.metric("Weight Score", f"{sample.get('weight_score', 'N/A')} / 10")
                with col3:
                    if pd.notna(sample.get("Heat treatment")):
                        st.metric("Heat Treatment", str(sample.get("Heat treatment")))
                    if pd.notna(sample.get("Std")):
                        st.metric("Standard", str(sample.get("Std")))
