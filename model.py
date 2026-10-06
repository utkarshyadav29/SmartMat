"""
model.py

Trains a Decision Tree Classifier to predict material recommendation categories
(1 of 5 buckets) based on strength and weight scores.

5 Recommendation Categories:
1. High Performance Composite (strength_score >= 8 and weight_score >= 7)
2. Structural Metal           (strength_score >= 7 and cost_score >= 7)
3. Lightweight Economy        (weight_score >= 8 and cost_score >= 8)
4. Eco-Friendly Material      (sustainability_score >= 7)
5. General Purpose            (otherwise)

Features (X):
- strength_score
- weight_score

Target (y):
- recommendation
"""

from pathlib import Path
import pickle
import warnings
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.tree import DecisionTreeClassifier
from sklearn.metrics import accuracy_score, classification_report

warnings.filterwarnings("ignore", category=UserWarning)


def assign_recommendation_bucket(row: pd.Series | dict) -> str:
    """
    Evaluate 5 recommendation categories based on criteria scores.
    """
    strength_score = float(row.get("strength_score", 0.0))
    weight_score = float(row.get("weight_score", 0.0))
    cost_score = float(row.get("cost_score", 5.0))
    sustainability_score = float(row.get("sustainability_score", 5.0))

    if strength_score >= 8 and weight_score >= 7:
        return "High Performance Composite"
    elif strength_score >= 7 and cost_score >= 7:
        return "Structural Metal"
    elif weight_score >= 8 and cost_score >= 8:
        return "Lightweight Economy"
    elif sustainability_score >= 7:
        return "Eco-Friendly Material"
    else:
        return "General Purpose"


def train_material_model(
    data_path: Path | str = "materials_scored.csv",
    model_path: Path | str = "model.pkl",
    test_size: float = 0.2,
    max_depth: int | None = 6,
    random_state: int = 42,
) -> tuple[DecisionTreeClassifier, float]:
    """
    Train a Decision Tree to predict material category recommendation.

    Args:
        data_path: Path to materials_scored.csv.
        model_path: Output path for model.pkl.
        test_size: Proportion of dataset for test split (default 0.2).
        max_depth: Maximum depth of decision tree (default 6).
        random_state: Random state seed.

    Returns:
        tuple of (trained DecisionTreeClassifier, test accuracy)
    """
    csv_file = Path(data_path)
    model_file = Path(model_path)

    if not csv_file.exists():
        raise FileNotFoundError(f"Dataset not found at: {csv_file.resolve()}")

    print(f"Loading data from: {csv_file.resolve()}")
    df = pd.read_csv(csv_file)

    # Ensure required feature columns exist
    feature_cols = ["strength_score", "weight_score"]
    for col in feature_cols:
        if col not in df.columns:
            raise KeyError(f"Required feature column '{col}' missing from {csv_file.name}")

    # Ensure recommendation column exists, or generate it dynamically
    if "recommendation" not in df.columns:
        print("Adding 'recommendation' column based on scoring rules...")
        df["recommendation"] = df.apply(assign_recommendation_bucket, axis=1)

    print("\nRecommendation class distribution:")
    print(df["recommendation"].value_counts())

    X = df[feature_cols]
    y = df["recommendation"]

    # Split dataset
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=test_size, random_state=random_state
    )

    # Train Decision Tree
    model = DecisionTreeClassifier(max_depth=max_depth, random_state=random_state)
    model.fit(X_train, y_train)

    # Evaluate accuracy
    y_pred = model.predict(X_test)
    accuracy = accuracy_score(y_test, y_pred)
    print(f"\n==========================================")
    print(f"Model Accuracy (Test Set): {accuracy:.4f} ({accuracy * 100:.2f}%)")
    print(f"==========================================\n")

    print("Detailed Classification Report:")
    print(classification_report(y_test, y_pred, zero_division=0))

    # Save model
    model_file.parent.mkdir(parents=True, exist_ok=True)
    with open(model_file, "wb") as f:
        pickle.dump(model, f)
    print(f"Saved trained category prediction model to: {model_file.resolve()}")

    return model, accuracy


if __name__ == "__main__":
    base_dir = Path(__file__).resolve().parent
    data_csv = base_dir / "materials_scored.csv"
    output_pkl = base_dir / "model.pkl"

    model, acc = train_material_model(data_path=data_csv, model_path=output_pkl)
