import hashlib
import hmac
import json
import os
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field


app = FastAPI(title="NSS Evidence Server")


class StartRunRequest(BaseModel):
    student_name: str = Field(min_length=1)
    student_id: str = Field(min_length=1)
    exercise_id: str = Field(min_length=1)
    computer: Dict[str, Any] = Field(default_factory=dict)


class EvidenceFile(BaseModel):
    path: str
    sha256: str
    size: int


class TimelineItem(BaseModel):
    time: str
    event: str


class SubmitEvidenceRequest(BaseModel):
    report_markdown: str
    timeline: List[TimelineItem] = Field(default_factory=list)
    files: List[EvidenceFile] = Field(default_factory=list)


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def get_db_path() -> Path:
    return Path(os.environ.get("NSS_EVIDENCE_DB", "data/evidence.db"))


def get_secret() -> str:
    return os.environ.get("NSS_EVIDENCE_SECRET", "dev-secret-change-me")


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def sha256_json(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def sign(run_id: str, evidence_hash: str, server_submitted_at: str) -> str:
    message = f"{run_id}:{evidence_hash}:{server_submitted_at}".encode("utf-8")
    return hmac.new(get_secret().encode("utf-8"), message, hashlib.sha256).hexdigest()


def connect() -> sqlite3.Connection:
    path = get_db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS runs (
            run_id TEXT PRIMARY KEY,
            student_name TEXT NOT NULL,
            student_id TEXT NOT NULL,
            exercise_id TEXT NOT NULL,
            computer_json TEXT NOT NULL,
            server_started_at TEXT NOT NULL,
            evidence_json TEXT,
            evidence_hash TEXT,
            signature TEXT,
            server_submitted_at TEXT
        )
        """
    )
    conn.commit()
    return conn


@app.post("/runs/start")
def start_run(payload: StartRunRequest) -> Dict[str, str]:
    run_id = "run_" + uuid.uuid4().hex
    server_started_at = now_iso()
    with connect() as conn:
        conn.execute(
            """
            INSERT INTO runs (
                run_id, student_name, student_id, exercise_id,
                computer_json, server_started_at
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                run_id,
                payload.student_name,
                payload.student_id,
                payload.exercise_id,
                canonical_json(payload.computer),
                server_started_at,
            ),
        )
        conn.commit()
    return {"run_id": run_id, "server_started_at": server_started_at}


@app.post("/runs/{run_id}/submit")
def submit_evidence(run_id: str, payload: SubmitEvidenceRequest) -> Dict[str, str]:
    evidence = payload.model_dump()
    evidence_hash = sha256_json(evidence)
    server_submitted_at = now_iso()
    signature = sign(run_id, evidence_hash, server_submitted_at)

    with connect() as conn:
        existing = conn.execute(
            "SELECT run_id FROM runs WHERE run_id = ?", (run_id,)
        ).fetchone()
        if existing is None:
            raise HTTPException(status_code=404, detail="run not found")
        conn.execute(
            """
            UPDATE runs
            SET evidence_json = ?, evidence_hash = ?, signature = ?, server_submitted_at = ?
            WHERE run_id = ?
            """,
            (
                canonical_json(evidence),
                evidence_hash,
                signature,
                server_submitted_at,
                run_id,
            ),
        )
        conn.commit()

    return {
        "run_id": run_id,
        "server_submitted_at": server_submitted_at,
        "evidence_hash": evidence_hash,
        "signature": signature,
    }


@app.get("/runs/{run_id}")
def get_run(run_id: str) -> Dict[str, Any]:
    with connect() as conn:
        row = conn.execute("SELECT * FROM runs WHERE run_id = ?", (run_id,)).fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="run not found")

    evidence: Optional[Dict[str, Any]] = None
    if row["evidence_json"]:
        evidence = json.loads(row["evidence_json"])

    return {
        "run_id": row["run_id"],
        "student_name": row["student_name"],
        "student_id": row["student_id"],
        "exercise_id": row["exercise_id"],
        "computer": json.loads(row["computer_json"]),
        "server_started_at": row["server_started_at"],
        "server_submitted_at": row["server_submitted_at"],
        "evidence_hash": row["evidence_hash"],
        "signature": row["signature"],
        "evidence": evidence,
    }
