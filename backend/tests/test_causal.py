import numpy as np
import pandas as pd
from app.services.causal import estimate_effect


def test_adjusted_effect_recovers_synthetic_dgp_and_differs_from_raw_association():
    rng = np.random.default_rng(7); c = rng.normal(size=1000); a = (c + rng.normal(size=1000) > 0).astype(int); y = 2.0 * a + 3.0 * c + rng.normal(size=1000)
    result = estimate_effect(pd.DataFrame({"C": c, "A": a, "Y": y}), "A", "Y", ["C"], "binary", [["C", "A"], ["C", "Y"], ["A", "Y"]])
    assert abs(result["estimated_effect"] - 2.0) < .2
    assert abs(result["estimated_effect"] - result["refutation_results"]["raw_difference_or_association"]) > .5
