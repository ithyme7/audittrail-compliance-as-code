from __future__ import annotations

import json
import os
from enum import Enum
from typing import Optional


class RiskLevel(str, Enum):
    MINIMAL = "MINIMAL"
    LIMITED = "LIMITED"
    HIGH = "HIGH"
    UNACCEPTABLE = "UNACCEPTABLE"


_CONFIG = {
    "initialized": False,
    "project": None,
    "risk_level": None,
    "output_dir": None,
}
_PREVIOUS_HASH = "0"


def _log_path() -> str:
    project = _CONFIG.get("project")
    output_dir = _CONFIG.get("output_dir")
    return os.path.join(output_dir, f"{project}_audit.log")


def init(project: str, risk_level: RiskLevel, output_dir: str = "./audit_logs") -> None:
    if not isinstance(risk_level, RiskLevel):
        raise ValueError("risk_level must be a RiskLevel enum value")

    os.makedirs(output_dir, exist_ok=True)
    _CONFIG["project"] = project
    _CONFIG["risk_level"] = risk_level
    _CONFIG["output_dir"] = output_dir

    global _PREVIOUS_HASH
    log_path = _log_path()
    _PREVIOUS_HASH = "0"
    if os.path.exists(log_path):
        try:
            with open(log_path, "r", encoding="utf-8") as f:
                lines = [line for line in f.read().splitlines() if line.strip()]
                if lines:
                    last = json.loads(lines[-1])
                    _PREVIOUS_HASH = last.get("hash", "0")
        except Exception:
            _PREVIOUS_HASH = "0"

    _CONFIG["initialized"] = True


def _ensure_initialized() -> None:
    if not _CONFIG.get("initialized"):
        raise RuntimeError("audittrail.init() must be called before using decorators")


def _get_config() -> dict:
    _ensure_initialized()
    return _CONFIG


def _get_previous_hash() -> str:
    _ensure_initialized()
    return _PREVIOUS_HASH


def _set_previous_hash(value: str) -> None:
    global _PREVIOUS_HASH
    _PREVIOUS_HASH = value


from .tracer import trace_inference, trace_training  # noqa: E402

def flush() -> None:
    from . import tracer as _tracer

    _tracer._flush_queue()


__all__ = ["init", "trace_training", "trace_inference", "RiskLevel", "flush"]
