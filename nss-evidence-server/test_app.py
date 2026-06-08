import json
import hmac
import hashlib
from pathlib import Path

from fastapi.testclient import TestClient

from app import app, get_db_path, get_secret


def test_start_run_returns_run_id_and_server_time(tmp_path, monkeypatch):
    monkeypatch.setenv("NSS_EVIDENCE_DB", str(tmp_path / "evidence.db"))
    monkeypatch.setenv("NSS_EVIDENCE_SECRET", "test-secret")

    client = TestClient(app)
    response = client.post(
        "/runs/start",
        json={
            "student_name": "张三",
            "student_id": "20240001",
            "exercise_id": "01-crypto-basic",
            "computer": {"os": "macOS", "cpu": "Apple M1"},
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["run_id"].startswith("run_")
    assert body["server_started_at"]


def test_submit_evidence_returns_verifiable_signature(tmp_path, monkeypatch):
    monkeypatch.setenv("NSS_EVIDENCE_DB", str(tmp_path / "evidence.db"))
    monkeypatch.setenv("NSS_EVIDENCE_SECRET", "test-secret")

    client = TestClient(app)
    start = client.post(
        "/runs/start",
        json={
            "student_name": "李四",
            "student_id": "20240002",
            "exercise_id": "02-crypto-inter",
            "computer": {"os": "Linux", "cpu": "x86_64"},
        },
    ).json()

    evidence = {
        "report_markdown": "# report",
        "timeline": [{"time": "2026-06-08T12:00:00Z", "event": "created solution.py"}],
        "files": [{"path": "solution.py", "sha256": "abc", "size": 123}],
    }
    response = client.post(f"/runs/{start['run_id']}/submit", json=evidence)

    assert response.status_code == 200
    body = response.json()
    canonical = json.dumps(
        evidence, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    )
    expected_hash = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    expected_signature = hmac.new(
        b"test-secret",
        f"{start['run_id']}:{expected_hash}:{body['server_submitted_at']}".encode(
            "utf-8"
        ),
        hashlib.sha256,
    ).hexdigest()

    assert body["evidence_hash"] == expected_hash
    assert body["signature"] == expected_signature


def test_homepage_serves_teacher_dashboard(tmp_path, monkeypatch):
    monkeypatch.setenv("NSS_EVIDENCE_DB", str(tmp_path / "evidence.db"))
    monkeypatch.setenv("NSS_EVIDENCE_SECRET", "test-secret")

    client = TestClient(app)
    response = client.get("/")

    assert response.status_code == 200
    assert "NSS Evidence Console" in response.text
    assert "证据签名" in response.text


def test_list_runs_returns_recent_submissions(tmp_path, monkeypatch):
    monkeypatch.setenv("NSS_EVIDENCE_DB", str(tmp_path / "evidence.db"))
    monkeypatch.setenv("NSS_EVIDENCE_SECRET", "test-secret")

    client = TestClient(app)
    start = client.post(
        "/runs/start",
        json={
            "student_name": "赵六",
            "student_id": "20240004",
            "exercise_id": "04-web-sec-basic",
            "computer": {"os": "macOS", "cpu": "Apple M3"},
        },
    ).json()
    client.post(
        f"/runs/{start['run_id']}/submit",
        json={"report_markdown": "# report", "timeline": [], "files": []},
    )

    response = client.get("/api/runs")

    assert response.status_code == 200
    body = response.json()
    assert body["runs"][0]["student_name"] == "赵六"
    assert body["runs"][0]["exercise_id"] == "04-web-sec-basic"
    assert body["runs"][0]["signature"]


def test_get_run_returns_saved_evidence(tmp_path, monkeypatch):
    monkeypatch.setenv("NSS_EVIDENCE_DB", str(tmp_path / "evidence.db"))
    monkeypatch.setenv("NSS_EVIDENCE_SECRET", "test-secret")

    client = TestClient(app)
    run = client.post(
        "/runs/start",
        json={
            "student_name": "王五",
            "student_id": "20240003",
            "exercise_id": "03-crypto-adv",
            "computer": {"os": "macOS", "cpu": "Apple M2"},
        },
    ).json()
    evidence = {"report_markdown": "# report", "timeline": [], "files": []}
    submitted = client.post(f"/runs/{run['run_id']}/submit", json=evidence).json()

    response = client.get(f"/runs/{run['run_id']}")

    assert response.status_code == 200
    body = response.json()
    assert body["run_id"] == run["run_id"]
    assert body["student_id"] == "20240003"
    assert body["evidence"] == evidence
    assert body["signature"] == submitted["signature"]
