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

from fastapi import Depends, FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse, Response
from pydantic import BaseModel, Field


app = FastAPI(title="NSS Evidence Server")

SESSION_COOKIE = "nss_teacher"


def get_teacher_user() -> str:
    return os.environ.get("NSS_TEACHER_USER", "admin").strip() or "admin"


def get_teacher_password() -> str:
    return os.environ.get("NSS_TEACHER_PASSWORD", "nsscli2026").strip() or "nsscli2026"


def make_session_token() -> str:
    msg = f"teacher:{get_teacher_user()}".encode("utf-8")
    return hmac.new(get_secret().encode("utf-8"), msg, hashlib.sha256).hexdigest()


def credentials_valid(username: str, password: str) -> bool:
    return secrets.compare_digest(
        username, get_teacher_user()
    ) and secrets.compare_digest(password, get_teacher_password())


def session_valid(token: Optional[str]) -> bool:
    if not token:
        return False
    return secrets.compare_digest(token, make_session_token())


def require_teacher(request: Request) -> None:
    if not session_valid(request.cookies.get(SESSION_COOKIE)):
        raise HTTPException(status_code=401, detail="教师端需要登录")


def require_teacher_page(request: Request) -> Optional[RedirectResponse]:
    if not session_valid(request.cookies.get(SESSION_COOKIE)):
        return RedirectResponse(url="/login", status_code=303)
    return None


def get_pdf_dir() -> Path:
    path = Path(os.environ.get("NSS_EVIDENCE_PDF_DIR", "data/pdf"))
    path.mkdir(parents=True, exist_ok=True)
    return path


FAVICON_SVG = (
    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32">'
    '<defs><linearGradient id="g" x1="0" y1="0" x2="1" y2="1">'
    '<stop offset="0" stop-color="#22d3ee"/><stop offset="1" stop-color="#8b5cf6"/>'
    "</linearGradient></defs>"
    '<rect width="32" height="32" rx="7" fill="url(#g)"/>'
    '<path d="M16 5l8 3v6c0 5-3.5 9-8 11-4.5-2-8-6-8-11V8z" fill="none" stroke="#05060f" stroke-width="2" stroke-linejoin="round"/>'
    '<path d="M12 16l3 3 5-6" fill="none" stroke="#05060f" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>'
    "</svg>"
)


@app.get("/favicon.ico")
def favicon() -> Response:
    return Response(content=FAVICON_SVG, media_type="image/svg+xml")


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


@app.get("/login", response_class=HTMLResponse)
def login_page(request: Request, error: str = ""):
    if session_valid(request.cookies.get(SESSION_COOKIE)):
        return RedirectResponse(url="/", status_code=303)
    err_html = f'<div class="err">{error}</div>' if error else ""
    return HTMLResponse(
        """
<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>NSS 教师端 · 登录</title>
  <link rel="icon" href="/favicon.ico" type="image/svg+xml" />
  <style>
    :root { color-scheme: dark; }
    * { box-sizing: border-box; }
    body { margin:0; min-height:100vh; display:flex; align-items:center; justify-content:center;
      font-family: ui-sans-serif, system-ui, -apple-system, "Segoe UI", sans-serif; color:#e5e7eb;
      background: radial-gradient(circle at 18% 12%, rgba(34,211,238,.22), transparent 30%),
        radial-gradient(circle at 82% 0%, rgba(139,92,246,.26), transparent 32%),
        linear-gradient(135deg,#020617,#0f172a 55%,#111827); }
    body::before { content:""; position:fixed; inset:0; pointer-events:none;
      background-image: linear-gradient(rgba(255,255,255,.04) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,.04) 1px, transparent 1px);
      background-size: 42px 42px; mask-image: linear-gradient(to bottom, rgba(0,0,0,.9), rgba(0,0,0,.1)); }
    .card { position:relative; width:min(400px, 92vw); background:rgba(15,23,42,.82);
      border:1px solid rgba(148,163,184,.22); border-radius:22px; padding:34px 30px;
      backdrop-filter: blur(18px); box-shadow:0 22px 70px rgba(0,0,0,.35); }
    .eyebrow { color:#22d3ee; letter-spacing:.24em; text-transform:uppercase; font-size:12px; font-weight:700; }
    h1 { margin:.4rem 0 4px; font-size:26px; }
    p.sub { color:#94a3b8; margin:0 0 24px; font-size:13px; }
    label { display:block; font-size:13px; color:#cbd5e1; margin:16px 0 6px; }
    input { width:100%; padding:12px 13px; border-radius:13px; border:1px solid rgba(148,163,184,.3);
      background:rgba(2,6,23,.65); color:#e5e7eb; font-size:14px; outline:none; }
    input:focus { border-color:rgba(34,211,238,.6); box-shadow:0 0 0 3px rgba(34,211,238,.12); }
    button { margin-top:26px; width:100%; padding:13px; border:none; border-radius:13px; cursor:pointer;
      background:linear-gradient(135deg,#22d3ee,#8b5cf6); color:#05060f; font-weight:800; font-size:15px;
      box-shadow:0 12px 30px rgba(34,211,238,.22); }
    .err { margin-top:16px; color:#fb7185; font-size:13px; }
  </style>
</head>
<body>
  <form class="card" method="post" action="/login">
    <div class="eyebrow">NSS · Teacher Console</div>
    <h1>教师端登录</h1>
    <p class="sub">证据查验控制台 · 请输入教师账号</p>
    <label>用户名</label>
    <input name="username" autocomplete="username" autofocus placeholder="admin" />
    <label>密码</label>
    <input name="password" type="password" autocomplete="current-password" placeholder="••••••••" />
    <button type="submit">登 录</button>
    __ERR__
  </form>
</body>
</html>
        """.replace("__ERR__", err_html)
    )


@app.post("/login")
def login_submit(username: str = Form(""), password: str = Form("")) -> Response:
    if not credentials_valid(username.strip(), password.strip()):
        return RedirectResponse(url="/login?error=用户名或密码错误", status_code=303)
    response = RedirectResponse(url="/", status_code=303)
    response.set_cookie(
        SESSION_COOKIE,
        make_session_token(),
        httponly=True,
        samesite="lax",
        max_age=60 * 60 * 12,
    )
    return response


@app.get("/logout")
def logout() -> Response:
    response = RedirectResponse(url="/login", status_code=303)
    response.delete_cookie(SESSION_COOKIE)
    return response


@app.get("/", response_class=HTMLResponse)
def homepage(request: Request):
    redirect = require_teacher_page(request)
    if redirect is not None:
        return redirect
    return HTMLResponse("""
<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>NSS Evidence Console</title>
  <link rel="icon" href="/favicon.ico" type="image/svg+xml" />
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
    .modal-mask { position:fixed; inset:0; background:rgba(2,6,23,.72); backdrop-filter:blur(4px); display:none; align-items:center; justify-content:center; z-index:50; padding:24px; }
    .modal-mask.show { display:flex; }
    .modal { width:min(760px, 94vw); max-height:84vh; display:flex; flex-direction:column; background:linear-gradient(180deg, rgba(17,25,42,.98), rgba(12,18,32,.98)); border:1px solid rgba(148,163,184,.25); border-radius:18px; box-shadow:0 30px 90px rgba(0,0,0,.6); }
    .modal-head { display:flex; align-items:center; justify-content:space-between; gap:12px; padding:18px 22px; border-bottom:1px solid var(--line); }
    .modal-head h3 { margin:0; font-size:16px; }
    .modal-close { cursor:pointer; border:1px solid rgba(148,163,184,.3); background:transparent; color:var(--muted); border-radius:8px; padding:5px 12px; font-size:13px; }
    .modal-close:hover { color:#fff; border-color:var(--cyan); }
    .modal-body { padding:18px 22px; overflow:auto; }
    .modal-body pre { white-space:pre-wrap; word-break:break-word; margin:0; font-size:13px; line-height:1.6; }
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
      <div style="display:flex;flex-direction:column;gap:10px;align-items:flex-end">
        <div class="hero-badge">证据签名 · HMAC-SHA256</div>
        <a href="/logout" style="color:#94a3b8;font-size:13px;text-decoration:none;border:1px solid rgba(148,163,184,.3);padding:6px 14px;border-radius:999px">退出登录</a>
      </div>
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
      if (res.status === 401) { window.location.href = '/login'; return }
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
      el('table').innerHTML = '<div class="table-wrap"><table><thead><tr><th>姓名</th><th>学号</th><th>实验</th><th>状态</th><th>提交编号</th><th>开始时间</th><th>提交时间</th><th>证据哈希 / 签名</th><th>报告(PDF)</th><th>操作</th></tr></thead><tbody>' + runs.map(r => `
        <tr>
          <td><b>${r.student_name}</b></td>
          <td><code>${r.student_id}</code></td>
          <td>${r.exercise_id}</td>
          <td>${renderBadge(r)}</td>
          <td><code>${r.run_id}</code></td>
          <td>${fmtTime(r.server_started_at)}</td>
          <td>${fmtTime(r.server_submitted_at)}</td>
          <td><code title="${r.evidence_hash || ''}">${shortHash(r.evidence_hash)}</code><br><code title="${r.signature || ''}">${shortHash(r.signature)}</code></td>
          <td>${r.pdf_path ? '<a class="btn-sm" style="display:inline-block;text-decoration:none" href="/runs/'+r.run_id+'/pdf" target="_blank">查看 PDF</a>' : '<span style="color:var(--muted);font-size:12px">未上传</span>'}</td>
          <td>${r.signature ? '<button class="btn-sm" onclick="verifyRun(\\''+r.run_id+'\\', this)">验证</button>' : ''}<button class="btn-sm" onclick="showQA('${r.run_id}')">查看 QA</button></td>
        </tr>`).join('') + '</tbody></table></div>'
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
    async function showQA(id) {
      const res = await fetch('/runs/' + id)
      if (res.status === 401) { window.location.href = '/login'; return }
      const run = await res.json()
      const esc = s => String(s || '').replace(/[<>&]/g, c => ({'<':'&lt;','>':'&gt;','&':'&amp;'}[c]))
      const qa = (run.qa_transcript || '').trim()
      const body = qa
        ? '<pre>' + esc(qa) + '</pre>'
        : '<div class="empty">无对话记录</div>'
      document.getElementById('modalTitle').textContent =
        '实验过程对话 — ' + run.student_name + '（' + run.student_id + '） · ' + run.exercise_id
      document.getElementById('modalBody').innerHTML = body
      document.getElementById('modalMask').classList.add('show')
    }
    function closeModal() { document.getElementById('modalMask').classList.remove('show') }
    el('query').addEventListener('input', render)
    el('exerciseFilter').addEventListener('change', render)
    el('statusFilter').addEventListener('change', render)
    document.getElementById('modalMask').addEventListener('click', e => { if (e.target.id === 'modalMask') closeModal() })
    document.addEventListener('keydown', e => { if (e.key === 'Escape') closeModal() })
    loadRuns()
  </script>
  <div class="modal-mask" id="modalMask">
    <div class="modal">
      <div class="modal-head">
        <h3 id="modalTitle">实验过程对话</h3>
        <button class="modal-close" onclick="closeModal()">关闭 ✕</button>
      </div>
      <div class="modal-body" id="modalBody"></div>
    </div>
  </div>
</body>
</html>
    """)


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
  <link rel="icon" href="/favicon.ico" type="image/svg+xml" />
  <style>
    :root { color-scheme: dark; --cyan:#22d3ee; --violet:#8b5cf6; --green:#34d399; --red:#fb7185; --muted:#8b97a8; }
    * { box-sizing: border-box; }
    body { margin:0; min-height:100vh; display:flex; align-items:center; justify-content:center; padding:48px 16px;
      font-family: ui-sans-serif, system-ui, -apple-system, "Segoe UI", "PingFang SC", sans-serif; color:#e5e7eb;
      background: radial-gradient(circle at 18% 8%, rgba(34,211,238,.20), transparent 30%),
        radial-gradient(circle at 84% 0%, rgba(139,92,246,.24), transparent 34%),
        linear-gradient(135deg,#020617,#0b1220 55%,#0f172a); }
    body::before { content:""; position:fixed; inset:0; pointer-events:none;
      background-image: linear-gradient(rgba(255,255,255,.035) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,.035) 1px, transparent 1px);
      background-size: 46px 46px; mask-image: linear-gradient(to bottom, rgba(0,0,0,.7), rgba(0,0,0,.05)); }
    .card { position:relative; width:min(580px, 94vw); background:linear-gradient(180deg, rgba(17,25,42,.9), rgba(12,18,32,.86));
      border:1px solid rgba(148,163,184,.18); border-radius:24px; padding:34px 36px 38px;
      backdrop-filter: blur(20px); box-shadow:0 30px 80px rgba(0,0,0,.45), inset 0 1px 0 rgba(255,255,255,.04); }
    .brand { display:flex; align-items:center; gap:14px; margin-bottom:22px; }
    .logo { width:46px; height:46px; border-radius:14px; display:grid; place-items:center; flex:none;
      background:linear-gradient(135deg, rgba(34,211,238,.9), rgba(139,92,246,.9)); box-shadow:0 8px 24px rgba(34,211,238,.28); }
    .logo svg { width:24px; height:24px; }
    .brand .eyebrow { color:var(--cyan); letter-spacing:.26em; text-transform:uppercase; font-size:11px; font-weight:800; }
    .brand h1 { margin:2px 0 0; font-size:23px; letter-spacing:.5px; }
    p.sub { color:var(--muted); margin:0 0 26px; font-size:13.5px; line-height:1.7; }
    p.sub b { color:#cbd5e1; }
    .search { display:flex; gap:10px; align-items:center; padding:8px; border-radius:16px;
      border:1px solid rgba(148,163,184,.22); background:rgba(2,6,23,.5); }
    .search label { font-size:13px; color:var(--muted); white-space:nowrap; padding-left:10px; }
    .search input { flex:1; min-width:0; padding:11px 8px; border:none; outline:none; background:transparent; color:#e5e7eb; font-size:14.5px; }
    .search input::placeholder { color:#5b6b80; }
    .search button { padding:11px 22px; border:none; border-radius:11px; cursor:pointer; white-space:nowrap;
      background:linear-gradient(135deg,var(--cyan),var(--violet)); color:#05060f; font-weight:800; font-size:14px;
      box-shadow:0 8px 22px rgba(34,211,238,.22); transition:transform .12s, box-shadow .12s; }
    .search button:hover { transform:translateY(-1px); box-shadow:0 12px 28px rgba(34,211,238,.32); }
    button:disabled { opacity:.5; cursor:not-allowed; transform:none !important; }
    #msg { font-size:13.5px; }
    #msg:not(:empty) { margin-top:16px; padding:11px 14px; border-radius:12px; }
    #msg.ok { color:var(--green); background:rgba(52,211,153,.1); border:1px solid rgba(52,211,153,.25); }
    #msg.err { color:var(--red); background:rgba(251,113,133,.1); border:1px solid rgba(251,113,133,.25); }
    .count { margin-top:24px; font-size:12px; color:var(--muted); letter-spacing:.04em; }
    .runs { display:flex; flex-direction:column; gap:14px; }
    .runs:not(:empty) { margin-top:10px; }
    .run { position:relative; border:1px solid rgba(148,163,184,.18); border-radius:18px; padding:18px 20px;
      background:linear-gradient(180deg, rgba(2,6,23,.55), rgba(2,6,23,.35)); transition:border-color .15s, transform .15s; }
    .run:hover { border-color:rgba(34,211,238,.35); transform:translateY(-1px); }
    .run-head { display:flex; align-items:center; gap:12px; }
    .ex-ic { width:38px; height:38px; border-radius:11px; flex:none; display:grid; place-items:center;
      background:rgba(34,211,238,.1); border:1px solid rgba(34,211,238,.25); }
    .ex-ic svg { width:19px; height:19px; }
    .run h3 { margin:0; font-size:15.5px; }
    .run .meta { color:var(--muted); font-size:11.5px; margin-top:3px; }
    .pill { font-size:11.5px; font-weight:700; padding:4px 12px; border-radius:999px; margin-left:auto; flex:none; }
    .pill.has { background:rgba(52,211,153,.14); color:var(--green); border:1px solid rgba(52,211,153,.3); }
    .pill.no { background:rgba(251,113,133,.12); color:var(--red); border:1px solid rgba(251,113,133,.28); }
    .run-actions { display:flex; gap:10px; align-items:center; flex-wrap:wrap; margin-top:16px;
      padding-top:14px; border-top:1px solid rgba(148,163,184,.12); }
    a.link { color:var(--cyan); font-size:13px; text-decoration:none; display:inline-flex; align-items:center; gap:5px;
      padding:7px 12px; border-radius:10px; border:1px solid rgba(34,211,238,.3); background:rgba(34,211,238,.06); transition:background .15s; }
    a.link:hover { background:rgba(34,211,238,.14); }
    .filewrap { display:inline-flex; align-items:center; gap:10px; flex:1; min-width:180px; }
    .filebtn { padding:7px 14px; border-radius:10px; border:1px dashed rgba(148,163,184,.4); background:transparent;
      color:#cbd5e1; font-size:13px; cursor:pointer; white-space:nowrap; transition:border-color .15s, color .15s; }
    .filebtn:hover { border-color:var(--cyan); color:#fff; }
    .fname { font-size:12px; color:var(--muted); overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }
    .run input[type=file] { display:none; }
    button.up { padding:8px 16px; border:none; border-radius:10px; cursor:pointer; white-space:nowrap; margin-left:auto;
      background:linear-gradient(135deg,var(--cyan),var(--violet)); color:#05060f; font-weight:700; font-size:13px; }
    .empty { color:var(--muted); font-size:13.5px; text-align:center; padding:30px 16px; margin-top:24px;
      border:1px dashed rgba(148,163,184,.22); border-radius:16px; background:rgba(2,6,23,.3); line-height:1.7; }
  </style>
</head>
<body>
  <div class="card">
    <div class="brand">
      <div class="logo">
        <svg viewBox="0 0 24 24" fill="none" stroke="#05060f" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><path d="M14 2v6h6"/><path d="M9 13h6M9 17h6"/></svg>
      </div>
      <div>
        <div class="eyebrow">NSS · Student</div>
        <h1>实验报告 PDF</h1>
      </div>
    </div>
    <p class="sub">PDF 仅供教师阅读，不参与签名验证。输入你的学号查询做过的实验，每个实验以你<b>最新一次</b>提交为准，可预览 / 替换 PDF。</p>
    <div class="search">
      <label for="sid">学号</label>
      <input id="sid" placeholder="如 20240001" />
      <button id="queryBtn">查询</button>
    </div>
    <div id="msg"></div>
    <div class="count" id="count"></div>
    <div class="runs" id="runs"></div>
  </div>
  <script>
    const $ = id => document.getElementById(id)
    const esc = s => String(s == null ? '' : s).replace(/[<>&"]/g, c => ({'<':'&lt;','>':'&gt;','&':'&amp;','"':'&quot;'}[c]))
    function fmt(t){ if(!t) return '-'; try{ return new Date(t).toLocaleString('zh-CN') }catch(e){ return t } }
    const fileIcon = '<svg viewBox="0 0 24 24" fill="none" stroke="#22d3ee" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><path d="M14 2v6h6"/></svg>'
    let currentSid = ''

    $('queryBtn').onclick = query
    $('sid').addEventListener('keydown', e => { if (e.key === 'Enter') query() })

    function setMsg(text, cls){ const m = $('msg'); m.textContent = text || ''; m.className = text ? cls : '' }

    async function query() {
      const sid = $('sid').value.trim()
      setMsg('', ''); $('runs').innerHTML = ''; $('count').textContent = ''
      if (!sid) { setMsg('请输入学号', 'err'); return }
      currentSid = sid
      const res = await fetch('/api/student/runs?student_id=' + encodeURIComponent(sid))
      const data = await res.json().catch(() => ({runs:[]}))
      const runs = data.runs || []
      if (!runs.length) { $('runs').innerHTML = '<div class="empty">没有查询到该学号的实验提交。<br>请先用 nsscli 做实验并 <b>report</b>。</div>'; return }
      $('count').textContent = '共 ' + runs.length + ' 个实验 · 学号 ' + sid
      $('runs').innerHTML = runs.map(r => `
        <div class="run">
          <div class="run-head">
            <div class="ex-ic">${fileIcon}</div>
            <div>
              <h3>${esc(r.exercise_id)}</h3>
              <div class="meta">最新提交 ${fmt(r.server_submitted_at)} · ${esc(r.run_id)}</div>
            </div>
            <span class="pill ${r.has_pdf ? 'has' : 'no'}">${r.has_pdf ? '已上传 PDF' : '未上传'}</span>
          </div>
          <div class="run-actions">
            ${r.has_pdf
              ? '<a class="link" href="/student/pdf?student_id='+encodeURIComponent(currentSid)+'&exercise_id='+encodeURIComponent(r.exercise_id)+'" target="_blank">预览当前 PDF</a>'
              : ''}
            <div class="filewrap">
              <input type="file" accept="application/pdf" id="f-${esc(r.exercise_id)}" />
              <button class="filebtn" type="button" data-for="f-${esc(r.exercise_id)}">选择 PDF</button>
              <span class="fname" data-fname="${esc(r.exercise_id)}">未选择文件</span>
            </div>
            <button class="up" data-ex="${esc(r.exercise_id)}">${r.has_pdf ? '替换' : '上传'}</button>
          </div>
        </div>`).join('')
      $('runs').querySelectorAll('.filebtn').forEach(btn => {
        btn.onclick = () => document.getElementById(btn.dataset.for).click()
      })
      $('runs').querySelectorAll('input[type=file]').forEach(inp => {
        inp.onchange = () => {
          const ex = inp.id.slice(2)
          const span = $('runs').querySelector('[data-fname="' + ex + '"]')
          span.textContent = inp.files[0] ? inp.files[0].name : '未选择文件'
        }
      })
      $('runs').querySelectorAll('button.up').forEach(btn => {
        btn.onclick = () => upload(btn.dataset.ex, btn)
      })
    }

    async function upload(exerciseId, btn) {
      const card = btn.closest('.run')
      const fileInput = card.querySelector('input[type=file]')
      const file = fileInput.files[0]
      setMsg('', '')
      if (!file) { setMsg('请先选择该实验的 PDF 文件', 'err'); return }
      const fd = new FormData()
      fd.append('student_id', currentSid)
      fd.append('exercise_id', exerciseId)
      fd.append('file', file)
      btn.disabled = true; const old = btn.textContent; btn.textContent = '上传中...'
      try {
        const res = await fetch('/student/pdf', { method: 'POST', body: fd })
        const data = await res.json().catch(() => ({}))
        if (!res.ok) throw new Error(data.detail || ('上传失败 (' + res.status + ')'))
        setMsg('✅ ' + exerciseId + ' 的报告 PDF 上传成功。', 'ok')
        await query()
      } catch (e) {
        setMsg('❌ ' + e.message, 'err')
        btn.disabled = false; btn.textContent = old
      }
    }
  </script>
</body>
</html>
    """


def _latest_run(conn, student_id: str, exercise_id: str):
    return conn.execute(
        """
        SELECT * FROM runs
        WHERE student_id = ? AND exercise_id = ? AND status = 'active'
        ORDER BY COALESCE(server_submitted_at, server_started_at) DESC
        LIMIT 1
        """,
        (student_id, exercise_id),
    ).fetchone()


@app.get("/api/student/runs")
def student_runs(student_id: str) -> Dict[str, Any]:
    student_id = (student_id or "").strip()
    if not student_id:
        raise HTTPException(status_code=400, detail="缺少学号")
    with connect() as conn:
        rows = conn.execute(
            """
            SELECT run_id, exercise_id, server_submitted_at, server_started_at, pdf_path
            FROM runs
            WHERE student_id = ? AND status = 'active'
            ORDER BY COALESCE(server_submitted_at, server_started_at) DESC
            """,
            (student_id,),
        ).fetchall()
    latest: Dict[str, Dict[str, Any]] = {}
    for row in rows:
        ex = row["exercise_id"]
        if ex in latest:
            continue
        latest[ex] = {
            "run_id": row["run_id"],
            "exercise_id": ex,
            "server_submitted_at": row["server_submitted_at"],
            "has_pdf": bool(row["pdf_path"]),
        }
    return {"runs": list(latest.values())}


@app.post("/student/pdf")
async def student_upload_pdf(
    student_id: str = Form(...),
    exercise_id: str = Form(...),
    file: UploadFile = File(...),
) -> Dict[str, str]:
    student_id = student_id.strip()
    exercise_id = exercise_id.strip()
    if not student_id or not exercise_id:
        raise HTTPException(status_code=400, detail="缺少学号或实验")

    filename = file.filename or ""
    if not filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="仅支持 PDF 文件")

    with connect() as conn:
        row = _latest_run(conn, student_id, exercise_id)
        if row is None:
            raise HTTPException(
                status_code=404, detail="未找到该学号该实验的提交，请先 report"
            )
        run_id = row["run_id"]

    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="文件为空")
    dest = get_pdf_dir() / f"{run_id}.pdf"
    dest.write_bytes(content)

    with connect() as conn:
        conn.execute(
            "UPDATE runs SET pdf_path = ? WHERE run_id = ?", (str(dest), run_id)
        )
        conn.commit()

    return {"run_id": run_id, "status": "uploaded"}


@app.get("/student/pdf")
def student_preview_pdf(student_id: str, exercise_id: str) -> FileResponse:
    student_id = (student_id or "").strip()
    exercise_id = (exercise_id or "").strip()
    with connect() as conn:
        row = _latest_run(conn, student_id, exercise_id)
    if row is None or not row["pdf_path"]:
        raise HTTPException(status_code=404, detail="该实验还没有上传 PDF")
    path = Path(row["pdf_path"])
    if not path.exists():
        raise HTTPException(status_code=404, detail="PDF 文件已丢失")
    return FileResponse(path, media_type="application/pdf")


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
