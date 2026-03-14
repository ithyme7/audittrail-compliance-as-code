import json
import os
import sys
from collections import Counter

import numpy as np
from sklearn.datasets import make_classification
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split

try:
    import audittrail  # noqa: E402
    from audittrail import RiskLevel, trace_inference, trace_training  # noqa: E402
    from audittrail.exporters.json_exporter import (  # noqa: E402
        export_compliance_report,
    )
    from audittrail.utils.integrity import verify_chain  # noqa: E402
except ImportError:
    SDK_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "sdk-python"))
    if SDK_PATH not in sys.path:
        sys.path.insert(0, SDK_PATH)
    import audittrail  # noqa: E402
    from audittrail import RiskLevel, trace_inference, trace_training  # noqa: E402
    from audittrail.exporters.json_exporter import (  # noqa: E402
        export_compliance_report,
    )
    from audittrail.utils.integrity import verify_chain  # noqa: E402


def _log_path(output_dir: str, project: str) -> str:
    return os.path.join(output_dir, f"{project}_audit.log")


def _read_entries(log_path: str):
    with open(log_path, "r", encoding="utf-8") as f:
        return [json.loads(line) for line in f.read().splitlines() if line.strip()]


def _latest_training_trace(entries):
    training_end = [e for e in entries if e["event_type"] == "training_end"]
    if not training_end:
        return None, None
    last = training_end[-1]
    return last["trace_id"], last.get("data", {}).get("compliance_checks")


def _count_human_review(pred_proba, threshold: float) -> int:
    max_conf = np.max(pred_proba, axis=1)
    return int(np.sum(max_conf > threshold))


def main():
    print("=== AuditTrail Fraud Detection Demo ===\n")

    project = "fraud-detection-demo"
    if getattr(sys, "frozen", False):
        base_dir = os.path.dirname(sys.executable)
    else:
        base_dir = os.path.dirname(os.path.abspath(__file__))
    output_dir = os.path.join(base_dir, "demo_output")
    audittrail.init(project=project, risk_level=RiskLevel.HIGH, output_dir=output_dir)

    X, y = make_classification(
        n_samples=1000,
        n_features=20,
        n_informative=15,
        n_redundant=5,
        n_classes=2,
        weights=[0.9, 0.1],
        random_state=42,
    )

    sensitive_attr = np.zeros(len(y), dtype=int)
    sensitive_attr[int(0.6 * len(y)) :] = 1

    rng = np.random.default_rng(42)
    group1_idx = np.where(sensitive_attr == 1)[0]
    flip_mask = rng.random(len(group1_idx)) < 0.15
    y[group1_idx[flip_mask]] = 1

    X_train, X_test, y_train, y_test, s_train, s_test = train_test_split(
        X, y, sensitive_attr, test_size=0.2, random_state=42
    )

    fraud_rate = float(np.mean(y))
    group_counts = Counter(sensitive_attr)
    print("Dataset Stats")
    print(f"- Total samples: {len(y)}")
    print(f"- Fraud rate: {fraud_rate:.3f}")
    print(f"- Group distribution: {dict(group_counts)}\n")

    @trace_training(dataset_version="synthetic-v1.0", fairness_metrics=["demographic_parity"])
    def train_model(X_train, y_train, sensitive_attr):
        model = RandomForestClassifier(n_estimators=100, random_state=42)
        model.fit(X_train, y_train)
        y_pred = model.predict(X_train)
        return {
            "model": model,
            "y_true": y_train,
            "y_pred": y_pred,
            "sensitive_attr": sensitive_attr,
        }

    training_result = train_model(X_train, y_train, s_train)
    model = training_result["model"]

    log_entries = _read_entries(_log_path(output_dir, project))
    trace_id, compliance_checks = _latest_training_trace(log_entries)
    print(f"Training completed, trace_id: {trace_id}")

    if compliance_checks and "demographic_parity" in compliance_checks:
        dp = compliance_checks["demographic_parity"]
        print(
            f"Demographic parity: value={dp['value']:.3f}, violates={dp['violates']}\n"
        )
    else:
        print("Demographic parity: not available\n")

    @trace_inference(require_human_review_threshold=0.85)
    def run_inference(X):
        return model.predict_proba(X)

    proba = run_inference(X_test[:20])
    print("Inference completed on 20 samples")
    review_count = _count_human_review(proba, threshold=0.85)
    print(f"Human review required for {review_count} samples\n")

    report_path = export_compliance_report()
    print(f"Compliance report exported to: {report_path}")

    log_path = _log_path(output_dir, project)
    chain_valid = verify_chain(log_path)
    print(f"Audit chain integrity: {'valid' if chain_valid else 'invalid'}\n")

    print("Summary")
    print("- Training and inference events logged")
    print("- Compliance metrics computed and stored")
    print("- Audit log integrity verified")
    print("- Compliance report generated")
    audittrail.flush()


if __name__ == "__main__":
    main()
