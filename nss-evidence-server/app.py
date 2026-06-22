import hashlib
import hmac
import json
import os
import secrets
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import Depends, FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from pydantic import BaseModel, Field


app = FastAPI(title="NSS Evidence Server")

_basic = HTTPBasic(auto_error=False)


def get_teacher_password() -> str:
    return os.environ.get("NSS_TEACHER_PASSWORD", "").strip()


def require_teacher(
    credentials: Optional[HTTPBasicCredentials] = Depends(_basic),
) -> None:
    password = get_teacher_password()
    if not password:
        return
    if credentials is None or not secrets.compare_digest(
        credentials.password, password
    ):
        raise HTTPException(
            status_code=401,
            detail="教师端需要密码",
            headers={"WWW-Authenticate": "Basic"},
        )


def get_pdf_dir() -> Path:
    path = Path(os.environ.get("NSS_EVIDENCE_PDF_DIR", "data/pdf"))
    path.mkdir(parents=True, exist_ok=True)
    return path


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


class FinalizeRequest(BaseModel):
    qa_transcript: str = ""
    final_report_markdown: str = ""
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
        ("qa_transcript", "qa_transcript TEXT"),
        ("pdf_path", "pdf_path TEXT"),
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
def homepage(_: None = Depends(require_teacher)) -> str:
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
    .hero-badge { border:1px solid rgba(34,211,238,.35); background:rgba(34,211,238,.08); color:#a5f3fc; padding:10px 14px; border-radius:999px; box-shadow:0 0 36px rgba(34,211,238,.18); white-space:nowrap; }
    .grid { display:grid; grid-template-columns: repeat(4, minmax(0,1fr)); gap:14px; margin:24px 0; }
    .card { background:var(--panel); border:1px solid var(--line); border-radius:20px; padding:18px; backdrop-filter: blur(18px); box-shadow:0 18px 60px rgba(0,0,0,.22); }
    .metric { font-size:28px; font-weight:800; margin-top:8px; }
    .label { color:var(--muted); font-size:13px; }
    .toolbar { display:flex; gap:12px; margin:22px 0; align-items:center; }
    input { flex:1; background:rgba(15,23,42,.88); border:1px solid var(--line); color:var(--text); padding:12px 16px; border-radius:12px; outline:none; height:44px; }
    button { border:0; border-radius:12px; padding:0 18px; height:44px; color:#06111f; font-weight:800; cursor:pointer; background:linear-gradient(135deg,var(--cyan),#a78bfa); }
    .table-wrap { overflow-x:auto; }
    table { width:100%; border-collapse:collapse; border-radius:18px; }
    th, td { text-align:left; padding:12px 14px; border-bottom:1px solid var(--line); font-size:13px; vertical-align:middle; white-space:nowrap; }
    th { color:#bae6fd; background:rgba(15,23,42,.92); position:sticky; top:0; }
    tr:hover td { background:rgba(34,211,238,.06); }
    code { color:#a5f3fc; }
    .ok { color:var(--green); font-weight:700; }
    .empty { color:var(--muted); padding:28px; text-align:center; }
    .details { white-space:pre-wrap; background:rgba(2,6,23,.75); border:1px solid var(--line); border-radius:14px; padding:14px; max-height:360px; overflow:auto; }
    .badge { display:inline-block; padding:4px 10px; border-radius:8px; font-size:12px; font-weight:700; }
    .badge-verified { background:rgba(52,211,153,.15); color:var(--green); border:1px solid rgba(52,211,153,.3); }
    .badge-pending { background:rgba(148,163,184,.12); color:var(--muted); border:1px solid rgba(148,163,184,.25); }
    .badge-superseded { background:rgba(251,146,60,.12); color:#fb923c; border:1px solid rgba(251,146,60,.25); }
    .badge-deleted { background:rgba(251,113,133,.12); color:var(--red); border:1px solid rgba(251,113,133,.25); }
    select { background:rgba(15,23,42,.88); border:1px solid var(--line); color:var(--text); padding:0 16px; border-radius:12px; outline:none; height:44px; cursor:pointer; min-width:130px; }
    .btn-sm { font-size:12px; font-weight:700; padding:6px 14px; height:30px; border-radius:8px; background:rgba(34,211,238,.12); color:var(--cyan); border:1px solid rgba(34,211,238,.3); }
    .btn-sm:hover { background:rgba(34,211,238,.22); }
    td .btn-sm + .btn-sm { margin-left:8px; }
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
      <div class="hero-badge">证据签名 · HMAC-SHA256</div>
    </section>
    <section class="grid">
      <div class="card"><div class="label">提交总数</div><div class="metric" id="total">-</div></div>
      <div class="card"><div class="label">已验证</div><div class="metric" id="verified">-</div></div>
      <div class="card"><div class="label">待提交</div><div class="metric" id="pending">-</div></div>
      <div class="card"><div class="label">学生数</div><div class="metric" id="students">-</div></div>
    </section>
    <section class="card">
      <div class="toolbar">
        <input id="query" placeholder="搜索：提交编号 / 学号 / 姓名 / 实验" />
        <select id="exerciseFilter"><option value="">全部实验</option></select>
        <select id="statusFilter">
          <option value="">全部状态</option>
          <option value="verified">已验证</option>
          <option value="pending">待提交</option>
          <option value="superseded">已取代</option>
          <option value="deleted">已删除</option>
        </select>
        <button onclick="loadRuns()">刷新</button>
      </div>
      <div id="table"></div>
    </section>
  </main>
  <script>
    const el = (id) => document.getElementById(id)
    let allRuns = []
    function statusKey(r) {
      if (r.status === 'deleted') return 'deleted'
      if (r.status === 'superseded') return 'superseded'
      if (r.verify_status === 'verified') return 'verified'
      return 'pending'
    }
    function renderBadge(r) {
      const k = statusKey(r)
      if (k === 'verified') return '<span class="badge badge-verified">✅已验证</span>'
      if (k === 'superseded') return '<span class="badge badge-superseded">🔄已取代</span>'
      if (k === 'deleted') return '<span class="badge badge-deleted">🗑已删除</span>'
      return '<span class="badge badge-pending">📝待提交</span>'
    }
    function fmtTime(t) {
      if (!t) return '-'
      return t.replace('T', ' ').replace('Z', '').split('.')[0]
    }
    function shortHash(h) {
      if (!h) return '-'
      return h.length > 24 ? h.slice(0, 12) + '…' + h.slice(-8) : h
    }
    function refreshExerciseOptions() {
      const sel = el('exerciseFilter')
      const current = sel.value
      const ids = [...new Set(allRuns.map(r => r.exercise_id))].sort()
      sel.innerHTML = '<option value="">全部实验</option>' + ids.map(id => `<option value="${id}">${id}</option>`).join('')
      sel.value = current
    }
    async function loadRuns() {
      const res = await fetch('/api/runs?status=all')
      const data = await res.json()
      allRuns = data.runs
      refreshExerciseOptions()
      render()
    }
    function render() {
      const q = el('query').value.trim().toLowerCase()
      const exFilter = el('exerciseFilter').value
      const stFilter = el('statusFilter').value
      const runs = allRuns.filter(r => {
        if (exFilter && r.exercise_id !== exFilter) return false
        if (stFilter && statusKey(r) !== stFilter) return false
        if (q && ![r.run_id, r.student_id, r.student_name, r.exercise_id].some(v => String(v || '').toLowerCase().includes(q))) return false
        return true
      })
      el('total').textContent = allRuns.length
      el('verified').textContent = allRuns.filter(r => statusKey(r) === 'verified').length
      el('pending').textContent = allRuns.filter(r => statusKey(r) === 'pending').length
      el('students').textContent = new Set(allRuns.map(r => r.student_id)).size
      if (!runs.length) { el('table').innerHTML = '<div class="empty">暂无符合条件的记录</div>'; return }
      el('table').innerHTML = '<div class="table-wrap"><table><thead><tr><th>姓名</th><th>学号</th><th>实验</th><th>状态</th><th>提交编号</th><th>开始时间</th><th>提交时间</th><th>证据哈希 / 签名</th><th>查看报告(QA)</th><th>操作</th></tr></thead><tbody>' + runs.map(r => `
        <tr>
          <td><b>${r.student_name}</b></td>
          <td><code>${r.student_id}</code></td>
          <td>${r.exercise_id}</td>
          <td>${renderBadge(r)}</td>
          <td><code>${r.run_id}</code></td>
          <td>${fmtTime(r.server_started_at)}</td>
          <td>${fmtTime(r.server_submitted_at)}</td>
          <td><code title="${r.evidence_hash || ''}">${shortHash(r.evidence_hash)}</code><br><code title="${r.signature || ''}">${shortHash(r.signature)}</code></td>
          <td><button class="btn-sm" onclick="showQA('${r.run_id}')">查看 QA</button>${r.pdf_path ? '<br><a class="btn-sm" style="display:inline-block;text-decoration:none;margin-top:4px" href="/runs/'+r.run_id+'/pdf" target="_blank">PDF</a>' : ''}</td>
          <td>${r.signature ? '<button class="btn-sm" onclick="verifyRun(\\''+r.run_id+'\\', this)">验证</button>' : ''}<button class="btn-sm" onclick="showRun('${r.run_id}')">查看</button></td>
        </tr>`).join('') + '</tbody></table></div><div id="detail" style="margin-top:16px"></div>'
    }
    async function verifyRun(id, btn) {
      btn.disabled = true
      btn.textContent = '...'
      try {
        const res = await fetch('/runs/' + id + '/verify')
        const data = await res.json()
        btn.textContent = data.signature_valid ? '✅ 有效' : '❌ 无效'
        btn.style.background = data.signature_valid ? 'rgba(52,211,153,.2)' : 'rgba(251,113,133,.2)'
        btn.style.color = data.signature_valid ? 'var(--green)' : 'var(--red)'
      } catch(e) {
        btn.textContent = '❌ 错误'
        btn.style.background = 'rgba(251,113,133,.2)'
        btn.style.color = 'var(--red)'
      }
    }
    async function showRun(id) {
      const res = await fetch('/runs/' + id)
      const run = await res.json()
      document.getElementById('detail').innerHTML = '<div class="details">' + JSON.stringify(run, null, 2).replace(/[<>&]/g, c => ({'<':'&lt;','>':'&gt;','&':'&amp;'}[c])) + '</div>'
    }
    async function showQA(id) {
      const res = await fetch('/runs/' + id)
      const run = await res.json()
      const esc = s => String(s || '').replace(/[<>&]/g, c => ({'<':'&lt;','>':'&gt;','&':'&amp;'}[c]))
      const qa = (run.qa_transcript || '').trim()
      const body = qa
        ? '<pre style="white-space:pre-wrap;word-break:break-word;margin:0">' + esc(qa) + '</pre>'
        : '<div class="empty">无对话记录</div>'
      document.getElementById('detail').innerHTML =
        '<div class="details"><div style="margin-bottom:8px;font-weight:600">实验过程对话 — ' + esc(run.student_name) + '（' + esc(run.student_id) + '） · ' + esc(run.exercise_id) + '</div>' + body + '</div>'
    }
    el('query').addEventListener('input', render)
    el('exerciseFilter').addEventListener('change', render)
    el('statusFilter').addEventListener('change', render)
    loadRuns()
  </script>
</body>
</html>
    """


@app.get("/api/runs")
def list_runs(
    status: str = "active", _: None = Depends(require_teacher)
) -> Dict[str, Any]:
    with connect() as conn:
        if status == "all":
            rows = conn.execute(
                """
                SELECT run_id, student_name, student_id, exercise_id,
                       server_started_at, server_submitted_at, evidence_hash,
                       signature, status, verify_status, pdf_path
                FROM runs
                ORDER BY COALESCE(server_submitted_at, server_started_at) DESC
                """
            ).fetchall()
        else:
            rows = conn.execute(
                """
                SELECT run_id, student_name, student_id, exercise_id,
                       server_started_at, server_submitted_at, evidence_hash,
                       signature, status, verify_status, pdf_path
                FROM runs
                WHERE status = ?
                ORDER BY COALESCE(server_submitted_at, server_started_at) DESC
                """,
                (status,),
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


@app.post("/runs/{run_id}/finalize")
def finalize_run(run_id: str, payload: FinalizeRequest) -> Dict[str, str]:
    server_submitted_at = now_iso()
    evidence_data = {"qa_transcript": payload.qa_transcript}
    evidence_hash = sha256_json(evidence_data)
    signature = sign(run_id, evidence_hash, server_submitted_at)

    with connect() as conn:
        row = conn.execute(
            "SELECT run_id, status, verify_status FROM runs WHERE run_id = ?", (run_id,)
        ).fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="run not found")
        if row["status"] != "active":
            raise HTTPException(status_code=409, detail="该记录已被取代或删除")
        if row["verify_status"] is not None:
            raise HTTPException(
                status_code=409, detail="已定版，请重新执行 report 开启新提交"
            )

        conn.execute(
            """
            UPDATE runs
            SET evidence_json = ?, evidence_hash = ?, signature = ?,
                server_submitted_at = ?, qa_transcript = ?,
                verify_status = 'verified', verified_at = ?
            WHERE run_id = ?
            """,
            (
                canonical_json(evidence_data),
                evidence_hash,
                signature,
                server_submitted_at,
                payload.qa_transcript,
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


@app.get("/runs/{run_id}/verify")
def verify_run(run_id: str, _: None = Depends(require_teacher)) -> Dict[str, Any]:
    with connect() as conn:
        row = conn.execute(
            "SELECT run_id, evidence_hash, signature, server_submitted_at, verify_status FROM runs WHERE run_id = ?",
            (run_id,),
        ).fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="run not found")
        if row["signature"] is None:
            raise HTTPException(status_code=400, detail="尚未定版，无法验证")

    expected_sig = sign(row["run_id"], row["evidence_hash"], row["server_submitted_at"])
    signature_valid = hmac.compare_digest(expected_sig, row["signature"])

    return {
        "run_id": run_id,
        "signature_valid": signature_valid,
        "verify_status": row["verify_status"],
        "evidence_hash": row["evidence_hash"],
        "server_submitted_at": row["server_submitted_at"],
    }


@app.delete("/runs/{run_id}")
def delete_run(run_id: str, _: None = Depends(require_teacher)) -> Dict[str, str]:
    with connect() as conn:
        row = conn.execute(
            "SELECT run_id FROM runs WHERE run_id = ?", (run_id,)
        ).fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="run not found")
        conn.execute("UPDATE runs SET status = 'deleted' WHERE run_id = ?", (run_id,))
        conn.commit()
    return {"run_id": run_id, "status": "deleted"}


@app.get("/runs/{run_id}")
def get_run(run_id: str, _: None = Depends(require_teacher)) -> Dict[str, Any]:
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
        "qa_transcript": row["qa_transcript"],
        "pdf_path": row["pdf_path"],
    }


@app.get("/student", response_class=HTMLResponse)
def student_page() -> str:
    return """
<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>NSS 学生端 · 报告上传</title>
  <style>
    :root { color-scheme: dark; }
    * { box-sizing: border-box; }
    body { margin:0; min-height:100vh; display:flex; align-items:center; justify-content:center;
      font-family: ui-sans-serif, system-ui, -apple-system, "Segoe UI", sans-serif; color:#e5e7eb;
      background: radial-gradient(circle at 20% 10%, rgba(34,211,238,.22), transparent 30%),
        radial-gradient(circle at 80% 0%, rgba(139,92,246,.26), transparent 32%),
        linear-gradient(135deg,#020617,#0f172a 55%,#111827); }
    .card { width:min(560px, 92vw); background:rgba(15,23,42,.82); border:1px solid rgba(148,163,184,.22);
      border-radius:20px; padding:32px; backdrop-filter: blur(18px); box-shadow:0 18px 60px rgba(0,0,0,.3); }
    .eyebrow { color:#22d3ee; letter-spacing:.22em; text-transform:uppercase; font-size:12px; font-weight:700; }
    h1 { margin:.35rem 0 4px; font-size:26px; }
    p.sub { color:#94a3b8; margin:0 0 22px; font-size:14px; line-height:1.6; }
    label { display:block; font-size:13px; color:#cbd5e1; margin:14px 0 6px; }
    input { width:100%; padding:11px 12px; border-radius:12px; border:1px solid rgba(148,163,184,.3);
      background:rgba(2,6,23,.6); color:#e5e7eb; font-size:14px; }
    button { margin-top:22px; width:100%; padding:12px; border:none; border-radius:12px; cursor:pointer;
      background:linear-gradient(135deg,#22d3ee,#8b5cf6); color:#05060f; font-weight:700; font-size:15px; }
    button:disabled { opacity:.5; cursor:not-allowed; }
    #msg { margin-top:16px; font-size:14px; min-height:20px; }
    .ok { color:#34d399; } .err { color:#fb7185; }
  </style>
</head>
<body>
  <div class="card">
    <div class="eyebrow">NSS · Student</div>
    <h1>实验报告 PDF 上传</h1>
    <p class="sub">PDF 仅供教师阅读，不参与签名验证。请填写你 report 时生成的提交编号（run_id），并选择报告 PDF 文件。</p>
    <label>提交编号 run_id</label>
    <input id="runId" placeholder="run_xxxxxxxx" />
    <label>报告 PDF</label>
    <input id="file" type="file" accept="application/pdf" />
    <button id="btn">上传</button>
    <div id="msg"></div>
  </div>
  <script>
    const $ = id => document.getElementById(id)
    $('btn').onclick = async () => {
      const runId = $('runId').value.trim()
      const file = $('file').files[0]
      const msg = $('msg')
      msg.textContent = ''; msg.className = ''
      if (!runId) { msg.textContent = '请填写提交编号 run_id'; msg.className = 'err'; return }
      if (!file) { msg.textContent = '请选择 PDF 文件'; msg.className = 'err'; return }
      const fd = new FormData()
      fd.append('file', file)
      $('btn').disabled = true; $('btn').textContent = '上传中...'
      try {
        const res = await fetch('/runs/' + encodeURIComponent(runId) + '/pdf', { method: 'POST', body: fd })
        const data = await res.json().catch(() => ({}))
        if (!res.ok) throw new Error(data.detail || ('上传失败 (' + res.status + ')'))
        msg.textContent = '✅ 上传成功，教师可在面板查看你的报告 PDF。'; msg.className = 'ok'
      } catch (e) {
        msg.textContent = '❌ ' + e.message; msg.className = 'err'
      } finally {
        $('btn').disabled = false; $('btn').textContent = '上传'
      }
    }
  </script>
</body>
</html>
    """


@app.post("/runs/{run_id}/pdf")
async def upload_pdf(run_id: str, file: UploadFile = File(...)) -> Dict[str, str]:
    with connect() as conn:
        row = conn.execute(
            "SELECT run_id FROM runs WHERE run_id = ?", (run_id,)
        ).fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="提交编号不存在，请确认 run_id")

    filename = file.filename or ""
    if not filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="仅支持 PDF 文件")

    dest = get_pdf_dir() / f"{run_id}.pdf"
    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="文件为空")
    dest.write_bytes(content)

    with connect() as conn:
        conn.execute(
            "UPDATE runs SET pdf_path = ? WHERE run_id = ?", (str(dest), run_id)
        )
        conn.commit()

    return {"run_id": run_id, "status": "uploaded"}


@app.get("/runs/{run_id}/pdf")
def download_pdf(run_id: str, _: None = Depends(require_teacher)) -> FileResponse:
    with connect() as conn:
        row = conn.execute(
            "SELECT pdf_path FROM runs WHERE run_id = ?", (run_id,)
        ).fetchone()
    if row is None or not row["pdf_path"]:
        raise HTTPException(status_code=404, detail="该提交没有 PDF")
    path = Path(row["pdf_path"])
    if not path.exists():
        raise HTTPException(status_code=404, detail="PDF 文件已丢失")
    return FileResponse(path, media_type="application/pdf", filename=f"{run_id}.pdf")
