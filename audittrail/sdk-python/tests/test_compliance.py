import numpy as np
import pytest

from audittrail.compliance import (
    calculate_fairness_metrics,
    demographic_parity_difference,
)


def test_demographic_parity_perfect_balance():
    y_true = np.array([0, 0, 1, 1])
    y_pred = np.array([0, 0, 1, 1])
    sensitive_attr = np.array([0, 1, 0, 1])
    result = demographic_parity_difference(y_true, y_pred, sensitive_attr)
    assert result["value"] == pytest.approx(0.0)
    assert result["violates"] is False


def test_demographic_parity_strong_bias():
    y_true = np.array([0, 0, 1, 1])
    y_pred = np.array([1, 1, 1, 0])
    sensitive_attr = np.array([0, 0, 1, 1])
    result = demographic_parity_difference(y_true, y_pred, sensitive_attr)
    assert result["value"] == pytest.approx(0.5)
    assert result["violates"] is True


def test_demographic_parity_threshold_boundary():
    y_true = np.zeros(40)
    sensitive_attr = np.array([0] * 20 + [1] * 20)
    y_pred = np.array([1] * 10 + [0] * 10 + [1] * 9 + [0] * 11)
    result = demographic_parity_difference(y_true, y_pred, sensitive_attr)
    assert result["value"] == pytest.approx(0.05)
    assert result["violates"] is False


def test_calculate_fairness_metrics_unknown_metric(caplog):
    y_true = np.array([0, 1])
    y_pred = np.array([0, 1])
    sensitive_attr = np.array([0, 1])
    with caplog.at_level("WARNING"):
        result = calculate_fairness_metrics(
            ["unknown_metric"], y_true, y_pred, sensitive_attr
        )
    assert result == {}
    assert any("Unknown fairness metric requested" in r.message for r in caplog.records)
