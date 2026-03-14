import json
import os
import tempfile
from unittest import mock

import pytest

import audittrail
from audittrail import trace_inference, trace_training, RiskLevel


@pytest.fixture
def temp_audit_dir():
    with tempfile.TemporaryDirectory() as tmp:
        audittrail.init(project="testproj", risk_level=RiskLevel.HIGH, output_dir=tmp)
        yield tmp


def _log_path(output_dir):
    return os.path.join(output_dir, "testproj_audit.log")


def _read_entries(path):
    with open(path, "r", encoding="utf-8") as f:
        return [json.loads(line) for line in f.read().splitlines() if line.strip()]


def test_init_creates_output_dir():
    with tempfile.TemporaryDirectory() as tmp:
        output_dir = os.path.join(tmp, "new_dir")
        audittrail.init(project="p1", risk_level=RiskLevel.MINIMAL, output_dir=output_dir)
        assert os.path.isdir(output_dir)


def test_trace_training_creates_log_file(temp_audit_dir):
    @trace_training(dataset_version="v1")
    def train():
        return {"ok": True}

    train()
    audittrail.flush()
    assert os.path.exists(_log_path(temp_audit_dir))


def test_trace_training_log_format(temp_audit_dir):
    @trace_training(dataset_version="v1")
    def train():
        return {"ok": True}

    train()
    audittrail.flush()
    entries = _read_entries(_log_path(temp_audit_dir))
    first = entries[0]
    for key in ["timestamp", "event_type", "trace_id", "project", "hash", "previous_hash"]:
        assert key in first


def test_trace_id_consistent_within_run(temp_audit_dir):
    @trace_training(dataset_version="v1")
    def train():
        return {"ok": True}

    train()
    audittrail.flush()
    entries = _read_entries(_log_path(temp_audit_dir))
    trace_ids = {e["trace_id"] for e in entries}
    assert len(trace_ids) == 1


def test_git_commit_detection(temp_audit_dir):
    @trace_training(dataset_version="v1")
    def train():
        return {"ok": True}

    with mock.patch("audittrail.tracer.subprocess.run") as mocked:
        mocked.return_value = mock.Mock(stdout="abc123\n")
        train()
    audittrail.flush()

    entries = _read_entries(_log_path(temp_audit_dir))
    training_end = [e for e in entries if e["event_type"] == "training_end"][-1]
    assert training_end["data"]["git_commit"] == "abc123"


def test_git_commit_none_outside_repo(temp_audit_dir):
    @trace_training(dataset_version="v1")
    def train():
        return {"ok": True}

    with mock.patch("audittrail.tracer.subprocess.run", side_effect=Exception("no git")):
        train()
    audittrail.flush()

    entries = _read_entries(_log_path(temp_audit_dir))
    training_end = [e for e in entries if e["event_type"] == "training_end"][-1]
    assert training_end["data"]["git_commit"] is None


def test_human_review_flag_high_confidence(temp_audit_dir):
    @trace_inference(require_human_review_threshold=0.5)
    def infer():
        return [0.9, 0.1]

    infer()
    audittrail.flush()
    entries = _read_entries(_log_path(temp_audit_dir))
    inference_end = [e for e in entries if e["event_type"] == "inference_end"][-1]
    assert inference_end["data"]["human_review_required"] is True


def test_human_review_flag_low_confidence(temp_audit_dir):
    @trace_inference(require_human_review_threshold=0.5)
    def infer():
        return [0.4, 0.1]

    infer()
    audittrail.flush()
    entries = _read_entries(_log_path(temp_audit_dir))
    inference_end = [e for e in entries if e["event_type"] == "inference_end"][-1]
    assert inference_end["data"]["human_review_required"] is False
