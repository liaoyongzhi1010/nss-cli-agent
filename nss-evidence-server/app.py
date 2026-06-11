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
from fastapi.responses import HTMLResponse
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
            server_submitted_at TEXT,
            final_report_md TEXT,
            verify_status TEXT,
            verified_at TEXT,
            verify_detail TEXT,
            status TEXT NOT NULL DEFAULT 'active'
        )
        """
    )
    for column, ddl in (
        ("final_report_md", "final_report_md TEXT"),
        ("verify_status", "verify_status TEXT"),
        ("verified_at", "verified_at TEXT"),
        ("verify_detail", "verify_detail TEXT"),
        ("status", "status TEXT NOT NULL DEFAULT 'active'"),
    ):
        try:
            conn.execute(f"ALTER TABLE runs ADD COLUMN {ddl}")
        except sqlite3.OperationalError:
            pass
    conn.commit()
    return conn


@app.get("/", response_class=HTMLResponse)
def homepage() -> str:
    return """
<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>NSS Evidence Console</title>
  <style>
    :root { color-scheme: dark; --bg:#050816; --panel:rgba(15,23,42,.78); --line:rgba(148,163,184,.22); --text:#e5e7eb; --muted:#94a3b8; --cyan:#22d3ee; --violet:#8b5cf6; --green:#34d399; --red:#fb7185; }
    * { box-sizing: border-box; }
    body { margin:0; min-height:100vh; font-family: ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; color:var(--text); background: radial-gradient(circle at 15% 10%, rgba(34,211,238,.22), transparent 28%), radial-gradient(circle at 80% 0%, rgba(139,92,246,.26), transparent 32%), linear-gradient(135deg,#020617,#0f172a 55%,#111827); }
    body::before { content:""; position:fixed; inset:0; pointer-events:none; background-image: linear-gradient(rgba(255,255,255,.04) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,.04) 1px, transparent 1px); background-size: 42px 42px; mask-image: linear-gradient(to bottom, rgba(0,0,0,.9), rgba(0,0,0,.15)); }
    .wrap { position:relative; max-width:1180px; margin:0 auto; padding:48px 24px; }
    .hero { display:flex; justify-content:space-between; gap:24px; align-items:flex-end; margin-bottom:24px; }
    .eyebrow { color:var(--cyan); letter-spacing:.22em; text-transform:uppercase; font-size:12px; font-weight:700; }
    h1 { margin:.35rem 0 0; font-size:44px; line-height:1; }
    .subtitle { color:var(--muted); margin-top:12px; font-size:15px; }
    .badge { border:1px solid rgba(34,211,238,.35); background:rgba(34,211,238,.08); color:#a5f3fc; padding:10px 14px; border-radius:999px; box-shadow:0 0 36px rgba(34,211,238,.18); white-space:nowrap; }
    .grid { display:grid; grid-template-columns: repeat(4, minmax(0,1fr)); gap:14px; margin:24px 0; }
    .card { background:var(--panel); border:1px solid var(--line); border-radius:20px; padding:18px; backdrop-filter: blur(18px); box-shadow:0 18px 60px rgba(0,0,0,.22); }
    .metric { font-size:28px; font-weight:800; margin-top:8px; }
    .label { color:var(--muted); font-size:13px; }
    .toolbar { display:flex; gap:12px; margin:22px 0; }
    input { flex:1; background:rgba(15,23,42,.88); border:1px solid var(--line); color:var(--text); padding:14px 16px; border-radius:14px; outline:none; }
    button { border:0; border-radius:14px; padding:14px 18px; color:#06111f; font-weight:800; cursor:pointer; background:linear-gradient(135deg,var(--cyan),#a78bfa); }
    table { width:100%; border-collapse:collapse; overflow:hidden; border-radius:18px; }
    th, td { text-align:left; padding:14px 16px; border-bottom:1px solid var(--line); font-size:14px; vertical-align:top; }
    th { color:#bae6fd; background:rgba(15,23,42,.92); position:sticky; top:0; }
    tr:hover td { background:rgba(34,211,238,.06); }
    code { color:#a5f3fc; word-break:break-all; }
    .ok { color:var(--green); font-weight:700; }
    .empty { color:var(--muted); padding:28px; text-align:center; }
    .details { white-space:pre-wrap; background:rgba(2,6,23,.75); border:1px solid var(--line); border-radius:14px; padding:14px; max-height:360px; overflow:auto; }
    @media (max-width: 820px) { .hero { display:block; } .grid { grid-template-columns:1fr 1fr; } h1 { font-size:34px; } }
  </style>
</head>
<body>
  <main class="wrap">
    <section class="hero">
      <div>
        <div class="eyebrow">NSS Evidence Console</div>
        <h1>实验过程证据中心</h1>
        <div class="subtitle">查询学生提交的证据包、服务器时间戳、文件哈希与防伪签名。</div>
      </div>
      <div class="badge">证据签名 · HMAC-SHA256</div>
    </section>
    <section class="grid">
      <div class="card"><div class="label">提交总数</div><div class="metric" id="total">-</div></div>
      <div class="card"><div class="label">已签名</div><div class="metric" id="signed">-</div></div>
      <div class="card"><div class="label">学生数</div><div class="metric" id="students">-</div></div>
      <div class="card"><div class="label">最新提交</div><div class="metric" id="latest" style="font-size:16px">-</div></div>
    </section>
    <section class="card">
      <div class="toolbar">
        <input id="query" placeholder="输入提交编号 / 学号 / 姓名 / 实验编号搜索" />
        <button onclick="loadRuns()">刷新</button>
      </div>
      <div id="table"></div>
    </section>
  </main>
  <script>
    const el = (id) => document.getElementById(id)
    async function loadRuns() {
      const q = el('query').value.trim().toLowerCase()
      const res = await fetch('/api/runs')
      const data = await res.json()
      const runs = data.runs.filter(r => !q || [r.run_id,r.student_id,r.student_name,r.exercise_id].some(v => String(v || '').toLowerCase().includes(q)))
      el('total').textContent = data.runs.length
      el('signed').textContent = data.runs.filter(r => r.signature).length
      el('students').textContent = new Set(data.runs.map(r => r.student_id)).size
      el('latest').textContent = data.runs[0]?.server_submitted_at || data.runs[0]?.server_started_at || '-'
      if (!runs.length) { el('table').innerHTML = '<div class="empty">暂无提交记录</div>'; return }
      el('table').innerHTML = '<table><thead><tr><th>学生</th><th>实验</th><th>提交编号</th><th>服务器时间</th><th>证据哈希 / 签名</th><th>详情</th></tr></thead><tbody>' + runs.map(r => `
        <tr>
          <td><b>${r.student_name}</b><br><code>${r.student_id}</code></td>
          <td>${r.exercise_id}</td>
          <td><code>${r.run_id}</code></td>
          <td>${r.server_submitted_at || r.server_started_at || '-'}</td>
          <td><div class="ok">${r.signature ? '已签名' : '未提交报告'}</div><code>${r.evidence_hash || '-'}</code><br><code>${r.signature || '-'}</code></td>
          <td><button onclick="showRun('${r.run_id}')">查看</button></td>
        </tr>`).join('') + '</tbody></table><div id="detail" style="margin-top:16px"></div>'
    }
    async function showRun(id) {
      const res = await fetch('/runs/' + id)
      const run = await res.json()
      document.getElementById('detail').innerHTML = '<div class="details">' + JSON.stringify(run, null, 2).replace(/[<>&]/g, c => ({'<':'&lt;','>':'&gt;','&':'&amp;'}[c])) + '</div>'
    }
    el('query').addEventListener('input', loadRuns)
    loadRuns()
  </script>
</body>
</html>
    """


@app.get("/api/runs")
def list_runs() -> Dict[str, Any]:
    with connect() as conn:
        rows = conn.execute(
            """
            SELECT run_id, student_name, student_id, exercise_id,
                   server_started_at, server_submitted_at, evidence_hash, signature
            FROM runs
            ORDER BY COALESCE(server_submitted_at, server_started_at) DESC
            """
        ).fetchall()
    return {"runs": [dict(row) for row in rows]}


@app.post("/runs/start")
def start_run(payload: StartRunRequest) -> Dict[str, str]:
    run_id = "run_" + uuid.uuid4().hex
    server_started_at = now_iso()
    with connect() as conn:
        conn.execute("BEGIN IMMEDIATE")
        conn.execute(
            """
            UPDATE runs SET status = 'superseded'
            WHERE student_id = ? AND exercise_id = ? AND status = 'active'
            """,
            (payload.student_id, payload.exercise_id),
        )
        conn.execute(
            """
            INSERT INTO runs (
                run_id, student_name, student_id, exercise_id,
                computer_json, server_started_at, status
            ) VALUES (?, ?, ?, ?, ?, ?, 'active')
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
        "status": row["status"],
        "verify_status": row["verify_status"],
        "verified_at": row["verified_at"],
        "verify_detail": row["verify_detail"],
        "final_report_md": row["final_report_md"],
    }
