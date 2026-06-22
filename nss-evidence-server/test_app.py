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


def test_schema_has_status_and_verify_columns(tmp_path, monkeypatch):
    monkeypatch.setenv("NSS_EVIDENCE_DB", str(tmp_path / "evidence.db"))
    monkeypatch.setenv("NSS_EVIDENCE_SECRET", "test-secret")

    client = TestClient(app)
    run = client.post(
        "/runs/start",
        json={
            "student_name": "测试",
            "student_id": "T001",
            "exercise_id": "01-crypto-basic",
            "computer": {},
        },
    ).json()
    detail = client.get(f"/runs/{run['run_id']}").json()
    assert detail["status"] == "active"
    assert detail["verify_status"] is None


def test_start_run_supersedes_previous_active_run(tmp_path, monkeypatch):
    monkeypatch.setenv("NSS_EVIDENCE_DB", str(tmp_path / "evidence.db"))
    monkeypatch.setenv("NSS_EVIDENCE_SECRET", "test-secret")

    client = TestClient(app)
    payload = {
        "student_name": "张三",
        "student_id": "20240001",
        "exercise_id": "01-crypto-basic",
        "computer": {},
    }
    first = client.post("/runs/start", json=payload).json()
    second = client.post("/runs/start", json=payload).json()

    first_detail = client.get(f"/runs/{first['run_id']}").json()
    second_detail = client.get(f"/runs/{second['run_id']}").json()
    assert first_detail["status"] == "superseded"
    assert second_detail["status"] == "active"


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


def test_finalize_returns_signature_and_marks_verified(tmp_path, monkeypatch):
    monkeypatch.setenv("NSS_EVIDENCE_DB", str(tmp_path / "evidence.db"))
    monkeypatch.setenv("NSS_EVIDENCE_SECRET", "test-secret")

    client = TestClient(app)
    run = client.post(
        "/runs/start",
        json={
            "student_name": "张三",
            "student_id": "20240001",
            "exercise_id": "01-crypto-basic",
            "computer": {},
        },
    ).json()

    qa = "## User\n帮我理解AES\n\n## Assistant\nAES是对称加密..."
    response = client.post(
        f"/runs/{run['run_id']}/finalize",
        json={"qa_transcript": qa},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["run_id"] == run["run_id"]
    assert body["signature"]
    assert body["evidence_hash"]
    assert body["server_submitted_at"]

    detail = client.get(f"/runs/{run['run_id']}").json()
    assert detail["verify_status"] == "verified"
    assert detail["signature"] == body["signature"]
    assert detail["qa_transcript"] == qa


def test_finalize_rejects_already_finalized_run(tmp_path, monkeypatch):
    monkeypatch.setenv("NSS_EVIDENCE_DB", str(tmp_path / "evidence.db"))
    monkeypatch.setenv("NSS_EVIDENCE_SECRET", "test-secret")

    client = TestClient(app)
    run = client.post(
        "/runs/start",
        json={
            "student_name": "张三",
            "student_id": "20240001",
            "exercise_id": "01-crypto-basic",
            "computer": {},
        },
    ).json()

    payload = {"qa_transcript": "## User\nhi\n## Assistant\nhello"}
    client.post(f"/runs/{run['run_id']}/finalize", json=payload)
    response = client.post(f"/runs/{run['run_id']}/finalize", json=payload)

    assert response.status_code == 409
    assert "已定版" in response.json()["detail"]


def test_verify_confirms_valid_signature(tmp_path, monkeypatch):
    monkeypatch.setenv("NSS_EVIDENCE_DB", str(tmp_path / "evidence.db"))
    monkeypatch.setenv("NSS_EVIDENCE_SECRET", "test-secret")

    client = TestClient(app)
    run = client.post(
        "/runs/start",
        json={
            "student_name": "张三",
            "student_id": "20240001",
            "exercise_id": "01-crypto-basic",
            "computer": {},
        },
    ).json()
    client.post(
        f"/runs/{run['run_id']}/finalize",
        json={"qa_transcript": "## User\nhi\n## Assistant\nhello"},
    )

    response = client.get(f"/runs/{run['run_id']}/verify")

    assert response.status_code == 200
    body = response.json()
    assert body["signature_valid"] is True
    assert body["verify_status"] == "verified"


def test_verify_detects_tampered_signature(tmp_path, monkeypatch):
    monkeypatch.setenv("NSS_EVIDENCE_DB", str(tmp_path / "evidence.db"))
    monkeypatch.setenv("NSS_EVIDENCE_SECRET", "test-secret")

    client = TestClient(app)
    run = client.post(
        "/runs/start",
        json={
            "student_name": "张三",
            "student_id": "20240001",
            "exercise_id": "01-crypto-basic",
            "computer": {},
        },
    ).json()
    client.post(
        f"/runs/{run['run_id']}/finalize",
        json={"qa_transcript": "## User\nhi\n## Assistant\nhello"},
    )

    import sqlite3

    db_path = tmp_path / "evidence.db"
    conn = sqlite3.connect(db_path)
    conn.execute(
        "UPDATE runs SET evidence_hash = 'tampered_hash' WHERE run_id = ?",
        (run["run_id"],),
    )
    conn.commit()
    conn.close()

    response = client.get(f"/runs/{run['run_id']}/verify")

    assert response.status_code == 200
    body = response.json()
    assert body["signature_valid"] is False


def test_delete_run_soft_deletes(tmp_path, monkeypatch):
    monkeypatch.setenv("NSS_EVIDENCE_DB", str(tmp_path / "evidence.db"))
    monkeypatch.setenv("NSS_EVIDENCE_SECRET", "test-secret")

    client = TestClient(app)
    run = client.post(
        "/runs/start",
        json={
            "student_name": "张三",
            "student_id": "20240001",
            "exercise_id": "01-crypto-basic",
            "computer": {},
        },
    ).json()

    response = client.delete(f"/runs/{run['run_id']}")
    assert response.status_code == 200

    detail = client.get(f"/runs/{run['run_id']}").json()
    assert detail["status"] == "deleted"


def test_list_runs_filters_by_status(tmp_path, monkeypatch):
    monkeypatch.setenv("NSS_EVIDENCE_DB", str(tmp_path / "evidence.db"))
    monkeypatch.setenv("NSS_EVIDENCE_SECRET", "test-secret")

    client = TestClient(app)
    payload = {
        "student_name": "张三",
        "student_id": "20240001",
        "exercise_id": "01-crypto-basic",
        "computer": {},
    }
    client.post("/runs/start", json=payload)
    client.post("/runs/start", json=payload)

    response_active = client.get("/api/runs?status=active")
    response_all = client.get("/api/runs?status=all")

    assert len(response_active.json()["runs"]) == 1
    assert len(response_all.json()["runs"]) == 2


def test_teacher_routes_require_password_when_set(tmp_path, monkeypatch):
    monkeypatch.setenv("NSS_EVIDENCE_DB", str(tmp_path / "evidence.db"))
    monkeypatch.setenv("NSS_EVIDENCE_SECRET", "test-secret")
    monkeypatch.setenv("NSS_TEACHER_PASSWORD", "s3cret")

    client = TestClient(app)

    assert client.get("/").status_code == 401
    assert client.get("/api/runs").status_code == 401

    ok = client.get("/api/runs", auth=("teacher", "s3cret"))
    assert ok.status_code == 200

    bad = client.get("/api/runs", auth=("teacher", "wrong"))
    assert bad.status_code == 401


def test_student_routes_open_without_password(tmp_path, monkeypatch):
    monkeypatch.setenv("NSS_EVIDENCE_DB", str(tmp_path / "evidence.db"))
    monkeypatch.setenv("NSS_EVIDENCE_SECRET", "test-secret")
    monkeypatch.setenv("NSS_TEACHER_PASSWORD", "s3cret")

    client = TestClient(app)

    assert client.get("/student").status_code == 200
    start = client.post(
        "/runs/start",
        json={
            "student_name": "张三",
            "student_id": "20240001",
            "exercise_id": "01-crypto-basic",
            "computer": {},
        },
    )
    assert start.status_code == 200


def test_pdf_upload_and_teacher_download(tmp_path, monkeypatch):
    monkeypatch.setenv("NSS_EVIDENCE_DB", str(tmp_path / "evidence.db"))
    monkeypatch.setenv("NSS_EVIDENCE_SECRET", "test-secret")
    monkeypatch.setenv("NSS_EVIDENCE_PDF_DIR", str(tmp_path / "pdf"))

    client = TestClient(app)
    run = client.post(
        "/runs/start",
        json={
            "student_name": "张三",
            "student_id": "20240001",
            "exercise_id": "01-crypto-basic",
            "computer": {},
        },
    ).json()

    pdf_bytes = b"%PDF-1.4 fake pdf content"
    upload = client.post(
        f"/runs/{run['run_id']}/pdf",
        files={"file": ("report.pdf", pdf_bytes, "application/pdf")},
    )
    assert upload.status_code == 200
    assert upload.json()["status"] == "uploaded"

    detail = client.get(f"/runs/{run['run_id']}").json()
    assert detail["pdf_path"]

    download = client.get(f"/runs/{run['run_id']}/pdf")
    assert download.status_code == 200
    assert download.content == pdf_bytes


def test_pdf_upload_rejects_non_pdf(tmp_path, monkeypatch):
    monkeypatch.setenv("NSS_EVIDENCE_DB", str(tmp_path / "evidence.db"))
    monkeypatch.setenv("NSS_EVIDENCE_SECRET", "test-secret")
    monkeypatch.setenv("NSS_EVIDENCE_PDF_DIR", str(tmp_path / "pdf"))

    client = TestClient(app)
    run = client.post(
        "/runs/start",
        json={
            "student_name": "张三",
            "student_id": "20240001",
            "exercise_id": "01-crypto-basic",
            "computer": {},
        },
    ).json()

    bad = client.post(
        f"/runs/{run['run_id']}/pdf",
        files={"file": ("report.txt", b"hello", "text/plain")},
    )
    assert bad.status_code == 400


def test_pdf_upload_unknown_run_returns_404(tmp_path, monkeypatch):
    monkeypatch.setenv("NSS_EVIDENCE_DB", str(tmp_path / "evidence.db"))
    monkeypatch.setenv("NSS_EVIDENCE_SECRET", "test-secret")
    monkeypatch.setenv("NSS_EVIDENCE_PDF_DIR", str(tmp_path / "pdf"))

    client = TestClient(app)
    resp = client.post(
        "/runs/run_does_not_exist/pdf",
        files={"file": ("report.pdf", b"%PDF-1.4", "application/pdf")},
    )
    assert resp.status_code == 404
