from __future__ import annotations

import datetime as _dt
import json
import logging
import os
import subprocess
import threading
import uuid
from typing import Any, Callable, Optional
import queue
import atexit

import audittrail
from audittrail import compliance
from audittrail.utils import integrity


logger = logging.getLogger(__name__)
_TLS = threading.local()
_HASH_LOCK = threading.Lock()
_LOG_QUEUE: "queue.Queue[dict | None]" = queue.Queue()
_WORKER_STARTED = False
_WORKER_LOCK = threading.Lock()
_MODE = os.getenv("AUDITTRAIL_MODE", "async").lower()


def _log_worker() -> None:
    while True:
        item = _LOG_QUEUE.get()
        if item is None:
            _LOG_QUEUE.task_done()
            break
        try:
            _write_log_entry_sync(item["event_type"], item["data"])
        finally:
            _LOG_QUEUE.task_done()


def _ensure_worker_started() -> None:
    global _WORKER_STARTED
    if _WORKER_STARTED:
        return
    with _WORKER_LOCK:
        if _WORKER_STARTED:
            return
        worker = threading.Thread(target=_log_worker, name="audittrail-log-writer", daemon=True)
        worker.start()
        _WORKER_STARTED = True


def _shutdown_worker() -> None:
    if not _WORKER_STARTED:
        return
    _LOG_QUEUE.put(None)
    _LOG_QUEUE.join()


def _flush_queue() -> None:
    if not _WORKER_STARTED:
        return
    _LOG_QUEUE.join()


atexit.register(_shutdown_worker)


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


def _write_log_entry_sync(event_type: str, data: dict) -> None:
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
    log_path = os.path.join(cfg["output_dir"], f"{cfg['project']}_audit.log")
    with _HASH_LOCK:
        previous_hash = audittrail._get_previous_hash()
        entry_hash = integrity.hash_entry(entry, previous_hash)
        entry["previous_hash"] = previous_hash
        entry["hash"] = entry_hash
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")
        audittrail._set_previous_hash(entry_hash)


def _write_log_entry(event_type: str, data: dict) -> None:
    if _MODE == "sync":
        _write_log_entry_sync(event_type, data)
        return
    _ensure_worker_started()
    _LOG_QUEUE.put({"event_type": event_type, "data": data})


def trace_training(dataset_version: str, fairness_metrics: list | None = None) -> Callable:
    def decorator(func: Callable) -> Callable:
        def wrapper(*args, **kwargs):
            audittrail._ensure_initialized()
            trace_id = str(uuid.uuid4())
            _TLS.trace_id = trace_id
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
            result = None
            status = "success"
            error_msg = None

            try:
                result = func(*args, **kwargs)
            except Exception as exc:
                status = "failed"
                error_msg = f"{type(exc).__name__}: {exc}"
                logger.error("Training failed: %s", error_msg)
                raise
            finally:
                end = _dt.datetime.now(_dt.timezone.utc)

                end_time = _utc_iso()
                duration_ms = int((end - start).total_seconds() * 1000)
                git_commit = _get_git_commit()

                hyperparameters = None
                if status == "success" and result is not None:
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
                if status == "success" and fairness_metrics:
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
                        "status": status,
                        "error": error_msg,
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
            _TLS.trace_id = trace_id

            input_shape = _shape_of(args[0]) if args else None
            _write_log_entry(
                "inference_start",
                {"trace_id": trace_id, "input_shape": input_shape},
            )

            result = None
            status = "success"
            error_msg = None
            try:
                result = func(*args, **kwargs)
            except Exception as exc:
                status = "failed"
                error_msg = f"{type(exc).__name__}: {exc}"
                logger.error("Inference failed: %s", error_msg)
                raise
            finally:
                output_shape = _shape_of(result) if status == "success" else None
                max_confidence = _max_confidence(result) if status == "success" else None
                human_review_required = None
                if (
                    status == "success"
                    and require_human_review_threshold is not None
                    and max_confidence is not None
                ):
                    human_review_required = max_confidence > require_human_review_threshold

                _write_log_entry(
                    "inference_end",
                    {
                        "trace_id": trace_id,
                        "status": status,
                        "error": error_msg,
                        "output_shape": output_shape,
                        "max_confidence": max_confidence,
                        "human_review_required": human_review_required,
                    },
                )
            return result

        return wrapper

    return decorator
