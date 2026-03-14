from __future__ import annotations

import logging
from typing import Dict, List

import numpy as np


logger = logging.getLogger(__name__)


def demographic_parity_difference(y_true, y_pred, sensitive_attr) -> Dict[str, float | bool]:
    y_true = np.asarray(y_true)
    y_pred = np.asarray(y_pred)
    sensitive_attr = np.asarray(sensitive_attr)

    if len(y_true) != len(y_pred) or len(y_true) != len(sensitive_attr):
        raise ValueError("y_true, y_pred, and sensitive_attr must have the same length")

    rate_0 = float(np.mean(y_pred[sensitive_attr == 0]))
    rate_1 = float(np.mean(y_pred[sensitive_attr == 1]))
    diff = abs(rate_0 - rate_1)
    threshold = 0.05
    return {"value": float(diff), "threshold": threshold, "violates": diff > threshold}


def calculate_fairness_metrics(
    metrics: List[str], y_true, y_pred, sensitive_attr
) -> Dict[str, dict]:
    results: Dict[str, dict] = {}
    for metric in metrics:
        if metric == "demographic_parity":
            results[metric] = demographic_parity_difference(y_true, y_pred, sensitive_attr)
        else:
            logger.warning("Unknown fairness metric requested: %s", metric)
    return results
