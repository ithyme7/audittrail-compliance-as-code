from __future__ import annotations

import hashlib
import json
import logging


logger = logging.getLogger(__name__)


def hash_entry(entry: dict, previous_hash: str) -> str:
    timestamp = entry.get("timestamp", "")
    event_type = entry.get("event_type", "")
    trace_id = entry.get("trace_id", "")
    data = entry.get("data", {})
    data_str = json.dumps(data, sort_keys=True, separators=(",", ":"))
    canonical = f"{timestamp}|{event_type}|{previous_hash}|{trace_id}|{data_str}"
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def verify_chain(log_path: str) -> bool:
    try:
        with open(log_path, "r", encoding="utf-8") as f:
            previous_hash = "0"
            for idx, line in enumerate(f, start=1):
                if not line.strip():
                    continue
                entry = json.loads(line)
                entry_prev = entry.get("previous_hash", "")
                expected_hash = hash_entry(entry, entry_prev)
                if entry.get("hash") != expected_hash:
                    logger.warning("Hash mismatch at line %s", idx)
                    return False
                if entry_prev != previous_hash:
                    logger.warning("Chain breach at line %s", idx)
                    return False
                previous_hash = entry.get("hash")
    except Exception as exc:
        logger.warning("verify_chain failed: %s", exc)
        return False

    return True
