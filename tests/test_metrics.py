import numpy as np
import pytest

from madrid_pollution.modeling.metrics import regression_metrics


def test_regression_metrics_are_stable_with_zero_values() -> None:
    metrics = regression_metrics(
        np.array([0.0, 10.0, 20.0]),
        np.array([0.0, 12.0, 18.0]),
        mase_scale=4.0,
    )

    assert metrics["mae"] == pytest.approx(4 / 3)
    assert metrics["mase"] == pytest.approx(1 / 3)
    assert np.isfinite(metrics["smape"])


def test_regression_metrics_reject_shape_mismatch() -> None:
    with pytest.raises(ValueError, match="same shape"):
        regression_metrics(np.array([1.0]), np.array([1.0, 2.0]), mase_scale=1.0)
