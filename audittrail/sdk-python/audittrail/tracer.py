from __future__ import annotations

import datetime as _dt
import json
import logging
import os
import subprocess
import uuid
from typing import Any, Callable, Optional

import audittrail
from audittrail import compliance
from audittrail.utils import integrity


logger = logging.getLogger(__name__)


def _utc_iso() -> str:
    return _dt.datetime.now(_dt.timezone.utc).isoformat()


def _get_git_commit() -> Optional[str]:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=True,
            text=True,
        )
        return result.stdout.strip()
    except Exception:
        return None


def _shape_of(obj: Any) -> Optional[tuple]:
    if obj is None:
        return None
    if hasattr(obj, "shape"):
        try:
            return tuple(obj.shape)
        except Exception:
            return None
    if isinstance(obj, (list, tuple)):
        if len(obj) == 0:
            return (0,)
        if isinstance(obj[0], (list, tuple)):
            return (len(obj), len(obj[0]))
        return (len(obj),)
    return None


def _max_confidence(output: Any) -> Optional[float]:
    if output is None:
        return None
    if hasattr(output, "shape") and len(getattr(output, "shape", [])) == 2:
        try:
            return float(output.max())
        except Exception:
            pass
    if isinstance(output, (list, tuple)) and output:
        if isinstance(output[0], (list, tuple)):
            try:
                return float(max(max(row) for row in output))
            except Exception:
                return None
        try:
            return float(max(output))
        except Exception:
            return None
    return None


def _write_log_entry(event_type: str, data: dict) -> None:
    cfg = audittrail._get_config()
    timestamp = _utc_iso()
    payload = dict(data)
    trace_id = payload.pop("trace_id", None)
    entry = {
        "timestamp": timestamp,
        "event_type": event_type,
        "trace_id": trace_id,
        "project": cfg["project"],
        "data": payload,
    }
    previous_hash = audittrail._get_previous_hash()
    entry_hash = integrity.hash_entry(entry, previous_hash)
    entry["previous_hash"] = previous_hash
    entry["hash"] = entry_hash

    log_path = os.path.join(cfg["output_dir"], f"{cfg['project']}_audit.log")
    with open(log_path, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")

    audittrail._set_previous_hash(entry_hash)


def trace_training(dataset_version: str, fairness_metrics: list | None = None) -> Callable:
    def decorator(func: Callable) -> Callable:
        def wrapper(*args, **kwargs):
            audittrail._ensure_initialized()
            trace_id = str(uuid.uuid4())
            start_time = _utc_iso()
            _write_log_entry(
                "training_start",
                {
                    "trace_id": trace_id,
                    "dataset_version": dataset_version,
                    "start_time": start_time,
                },
            )

            start = _dt.datetime.now(_dt.timezone.utc)
            result = func(*args, **kwargs)
            end = _dt.datetime.now(_dt.timezone.utc)

            end_time = _utc_iso()
            duration_ms = int((end - start).total_seconds() * 1000)
            git_commit = _get_git_commit()

            hyperparameters = None
            if hasattr(result, "get_params"):
                try:
                    hyperparameters = result.get_params()
                except Exception:
                    hyperparameters = None
            elif isinstance(result, dict) and "model" in result and hasattr(
                result["model"], "get_params"
            ):
                try:
                    hyperparameters = result["model"].get_params()
                except Exception:
                    hyperparameters = None

            compliance_checks = None
            compliance_warning = None
            if fairness_metrics:
                y_true = kwargs.get("y_true")
                y_pred = kwargs.get("y_pred")
                sensitive_attr = kwargs.get("sensitive_attr")
                if y_true is None and isinstance(result, dict):
                    y_true = result.get("y_true")
                    y_pred = result.get("y_pred")
                    sensitive_attr = result.get("sensitive_attr")
                if y_true is not None and y_pred is not None and sensitive_attr is not None:
                    compliance_checks = compliance.calculate_fairness_metrics(
                        fairness_metrics, y_true, y_pred, sensitive_attr
                    )
                else:
                    compliance_warning = (
                        "fairness_metrics requested but inputs (y_true, y_pred, sensitive_attr) missing"
                    )

            _write_log_entry(
                "training_end",
                {
                    "trace_id": trace_id,
                    "end_time": end_time,
                    "duration_ms": duration_ms,
                    "git_commit": git_commit,
                    "hyperparameters": hyperparameters,
                    "compliance_checks": compliance_checks,
                    "compliance_warning": compliance_warning,
                },
            )
            return result

        return wrapper

    return decorator


def trace_inference(require_human_review_threshold: float | None = None) -> Callable:
    def decorator(func: Callable) -> Callable:
        def wrapper(*args, **kwargs):
            audittrail._ensure_initialized()
            trace_id = str(uuid.uuid4())

            input_shape = _shape_of(args[0]) if args else None
            _write_log_entry(
                "inference_start",
                {"trace_id": trace_id, "input_shape": input_shape},
            )

            result = func(*args, **kwargs)

            output_shape = _shape_of(result)
            max_confidence = _max_confidence(result)
            human_review_required = None
            if require_human_review_threshold is not None and max_confidence is not None:
                human_review_required = max_confidence > require_human_review_threshold

            _write_log_entry(
                "inference_end",
                {
                    "trace_id": trace_id,
                    "output_shape": output_shape,
                    "max_confidence": max_confidence,
                    "human_review_required": human_review_required,
                },
            )
            return result

        return wrapper

    return decorator
