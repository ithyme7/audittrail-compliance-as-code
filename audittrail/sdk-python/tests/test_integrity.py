import json
import tempfile

from audittrail.utils.integrity import hash_entry, verify_chain


def _make_entry(timestamp, event_type, trace_id, previous_hash):
    entry = {
        "timestamp": timestamp,
        "event_type": event_type,
        "trace_id": trace_id,
        "project": "p1",
        "data": {},
    }
    entry_hash = hash_entry(entry, previous_hash)
    entry["previous_hash"] = previous_hash
    entry["hash"] = entry_hash
    return entry


def test_hash_entry_deterministic():
    entry = {"timestamp": "t", "event_type": "e", "trace_id": "id1"}
    h1 = hash_entry(entry, "0")
    h2 = hash_entry(entry, "0")
    assert h1 == h2


def test_hash_chain_valid():
    entries = []
    prev = "0"
    for i in range(3):
        e = _make_entry(f"t{i}", f"event{i}", f"id{i}", prev)
        entries.append(e)
        prev = e["hash"]

    with tempfile.NamedTemporaryFile(mode="w+", delete=False) as f:
        for e in entries:
            f.write(json.dumps(e) + "\n")
        path = f.name

    assert verify_chain(path) is True


def test_hash_chain_tampering_detected():
    entries = []
    prev = "0"
    for i in range(3):
        e = _make_entry(f"t{i}", f"event{i}", f"id{i}", prev)
        entries.append(e)
        prev = e["hash"]

    entries[1]["data"] = {"tampered": True}

    with tempfile.NamedTemporaryFile(mode="w+", delete=False) as f:
        for e in entries:
            f.write(json.dumps(e) + "\n")
        path = f.name

    assert verify_chain(path) is False
