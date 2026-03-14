from __future__ import annotations

import datetime as _dt
import json
import os
from collections import defaultdict
from typing import List, Optional

import audittrail


def export_compliance_report(
    trace_ids: List[str] | None = None, output_path: str | None = None
) -> str:
    cfg = audittrail._get_config()
    log_path = os.path.join(cfg["output_dir"], f"{cfg['project']}_audit.log")
    if not os.path.exists(log_path):
        raise FileNotFoundError(f"Log file not found: {log_path}")

    entries = []
    with open(log_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            entries.append(json.loads(line))

    if trace_ids is None:
        trace_ids = sorted({e.get("trace_id") for e in entries if e.get("trace_id")})

    entries = [e for e in entries if e.get("trace_id") in trace_ids]

    traces = []
    violations_found = 0
    grouped = defaultdict(list)
    for e in entries:
        grouped[e.get("trace_id")].append(e)

    for trace_id, events in grouped.items():
        compliance_checks = {}
        for e in events:
            checks = e.get("data", {}).get("compliance_checks")
            if isinstance(checks, dict):
                compliance_checks.update(checks)
        for _, val in compliance_checks.items():
            if isinstance(val, dict) and val.get("violates"):
                violations_found += 1
        traces.append(
            {
                "trace_id": trace_id,
                "events": events,
                "compliance_checks": compliance_checks,
            }
        )

    summary = {
        "total_traces": len(traces),
        "total_events": len(entries),
        "violations_found": violations_found,
    }

    generated_at = _dt.datetime.now(_dt.timezone.utc).isoformat()
    report = {
        "project": cfg["project"],
        "generated_at": generated_at,
        "risk_level": cfg["risk_level"].value if cfg.get("risk_level") else None,
        "traces": traces,
        "summary": summary,
    }

    if output_path is None:
        safe_ts = generated_at.replace(":", "").replace("+", "")
        output_path = os.path.join(
            cfg["output_dir"], f"{cfg['project']}_compliance_report_{safe_ts}.json"
        )

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    return output_path
