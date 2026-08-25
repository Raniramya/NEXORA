from __future__ import annotations

from typing import Any

import joblib
import numpy as np


def explain_fault_prediction(artifact_location: str, features: dict[str, float], predicted_class: str, *, seed: int = 42, permutations: int = 128) -> dict[str, Any]:
    artifact = joblib.load(artifact_location)
    model = artifact["model"]
    names = artifact["feature_names"]
    missing = [name for name in names if name not in features]
    if missing:
        raise ValueError(f"Feature set is missing required features: {', '.join(missing)}")
    if not hasattr(model, "predict_proba"):
        raise ValueError("The persisted classifier does not expose class probabilities.")
    classes = [str(value) for value in model.classes_]
    if predicted_class not in classes:
        raise ValueError("Predicted class is not present in the model artifact.")
    class_index = classes.index(predicted_class)
    row = np.asarray([[features[name] for name in names]], dtype=np.float64)
    background = np.asarray(artifact["background"], dtype=np.float64)
    reference = np.mean(background, axis=0, keepdims=True)
    base_value = float(model.predict_proba(reference)[0, class_index])
    output_value = float(model.predict_proba(row)[0, class_index])
    rng = np.random.default_rng(seed)
    contributions = np.zeros(len(names), dtype=np.float64)
    for _ in range(permutations):
        working = reference.copy()
        previous = base_value
        for feature_index in rng.permutation(len(names)):
            working[0, feature_index] = row[0, feature_index]
            current = float(model.predict_proba(working)[0, class_index])
            contributions[feature_index] += current - previous
            previous = current
    contributions /= permutations
    return {
        "method": "permutation_shap",
        "explained_class": predicted_class,
        "base_value": base_value,
        "output_value": output_value,
        "contributions": {name: float(value) for name, value in zip(names, contributions)},
        "feature_values": {name: float(features[name]) for name in names},
        "configuration": {"seed": seed, "permutations": permutations, "background_size": len(background), "reference": "training_background_mean"},
    }
