# Manual Upload + Auto-Verify Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement three-step lesson flow (init/report/submit) with server-side auto-verification, soft-delete, and teacher dashboard badges.

**Architecture:** Backend adds `finalize` + `verify` endpoints + `status`/`verify_status` columns; nsscli splits report/submit into two separate actions; teacher dashboard shows verification badges with status filtering.

**Tech Stack:** Python/FastAPI/SQLite (backend), TypeScript/Ink (nsscli TUI)

---

## File Structure

### Backend (`nss-evidence-server/`)
- Modify: `app.py` — add finalize/verify/delete endpoints, schema migration, soft-delete logic, update start for superseded, update dashboard HTML
- Modify: `test_app.py` — new tests for finalize, verify, soft-delete, superseded, repeat-finalize

### nsscli (`nss-cli-agent/packages/opencode/src/cli/cmd/tui/`)
- Modify: `component/lab-evidence.ts` — add `finalizeEvidence()`, `writeReportSkeleton()`, remove old `submitEvidence` from report flow
- Modify: `component/dialog-lesson-actions.tsx` — add `submit` option + `onSubmit` prop
- Modify: `app.tsx` — rewire `onReport` (no upload), add `onSubmit` handler

---

### Task 1: Backend — Schema Migration (add columns)

**Files:**
- Modify: `nss-evidence-server/app.py:68-90` (connect function)

- [ ] **Step 1: Write failing test for new columns**

Add to `test_app.py`:
```python
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd nss-evidence-server && .venv/bin/pytest test_app.py::test_schema_has_status_and_verify_columns -v`
Expected: FAIL (KeyError: 'status')

- [ ] **Step 3: Update schema in connect()**

In `app.py`, replace the `CREATE TABLE` statement and add migration logic:
```python
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
    # Migrate existing tables
    for col, typedef in [
        ("final_report_md", "TEXT"),
        ("verify_status", "TEXT"),
        ("verified_at", "TEXT"),
        ("verify_detail", "TEXT"),
        ("status", "TEXT NOT NULL DEFAULT 'active'"),
    ]:
        try:
            conn.execute(f"ALTER TABLE runs ADD COLUMN {col} {typedef}")
        except sqlite3.OperationalError:
            pass
    conn.commit()
    return conn
```

- [ ] **Step 4: Update get_run to return new fields**

In `app.py` `get_run` function, add new fields to the return dict:
```python
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
        "verify_detail": json.loads(row["verify_detail"]) if row["verify_detail"] else None,
        "final_report_md": row["final_report_md"],
    }
```

- [ ] **Step 5: Run test to verify it passes**

Run: `cd nss-evidence-server && .venv/bin/pytest test_app.py::test_schema_has_status_and_verify_columns -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add nss-evidence-server/app.py nss-evidence-server/test_app.py
git commit -m "feat(evidence): add status + verify columns with migration"
```

---

### Task 2: Backend — Soft-delete on start (superseded logic)

**Files:**
- Modify: `nss-evidence-server/app.py:204-226` (start_run)
- Modify: `nss-evidence-server/test_app.py`

- [ ] **Step 1: Write failing test for superseded**

Add to `test_app.py`:
```python
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd nss-evidence-server && .venv/bin/pytest test_app.py::test_start_run_supersedes_previous_active_run -v`
Expected: FAIL (first_detail["status"] == "active")

- [ ] **Step 3: Update start_run with atomic supersede**

Replace `start_run` in `app.py`:
```python
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd nss-evidence-server && .venv/bin/pytest test_app.py::test_start_run_supersedes_previous_active_run -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add nss-evidence-server/app.py nss-evidence-server/test_app.py
git commit -m "feat(evidence): supersede previous active run on start"
```

---

### Task 3: Backend — Finalize endpoint

**Files:**
- Modify: `nss-evidence-server/app.py` — add `FinalizeRequest` model + `POST /runs/{id}/finalize`
- Modify: `nss-evidence-server/test_app.py`

- [ ] **Step 1: Write failing test for finalize happy path**

Add to `test_app.py`:
```python
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

    final_report = "# 实验报告\n\n正文内容"
    files = [{"path": "solution.py", "sha256": "abc123", "size": 200}]
    response = client.post(
        f"/runs/{run['run_id']}/finalize",
        json={"final_report_markdown": final_report, "files": files},
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
```

- [ ] **Step 2: Write failing test for repeat finalize rejection**

Add to `test_app.py`:
```python
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

    payload = {"final_report_markdown": "# report", "files": []}
    client.post(f"/runs/{run['run_id']}/finalize", json=payload)
    response = client.post(f"/runs/{run['run_id']}/finalize", json=payload)

    assert response.status_code == 409
    assert "已定版" in response.json()["detail"]
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `cd nss-evidence-server && .venv/bin/pytest test_app.py::test_finalize_returns_signature_and_marks_verified test_app.py::test_finalize_rejects_already_finalized_run -v`
Expected: FAIL (404, endpoint not found)

- [ ] **Step 4: Add FinalizeRequest model and finalize endpoint**

Add to `app.py` after `SubmitEvidenceRequest`:
```python
class FinalizeRequest(BaseModel):
    final_report_markdown: str
    files: List[EvidenceFile] = Field(default_factory=list)
```

Add endpoint after `submit_evidence`:
```python
@app.post("/runs/{run_id}/finalize")
def finalize_run(run_id: str, payload: FinalizeRequest) -> Dict[str, str]:
    server_submitted_at = now_iso()
    evidence_data = {"final_report_markdown": payload.final_report_markdown, "files": [f.model_dump() for f in payload.files]}
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
            raise HTTPException(status_code=409, detail="已定版，请重新执行 report 开启新提交")

        conn.execute(
            """
            UPDATE runs
            SET evidence_json = ?, evidence_hash = ?, signature = ?,
                server_submitted_at = ?, final_report_md = ?,
                verify_status = 'verified', verified_at = ?
            WHERE run_id = ?
            """,
            (
                canonical_json(evidence_data),
                evidence_hash,
                signature,
                server_submitted_at,
                payload.final_report_markdown,
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
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `cd nss-evidence-server && .venv/bin/pytest test_app.py::test_finalize_returns_signature_and_marks_verified test_app.py::test_finalize_rejects_already_finalized_run -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add nss-evidence-server/app.py nss-evidence-server/test_app.py
git commit -m "feat(evidence): add POST /runs/{id}/finalize endpoint"
```

---

### Task 4: Backend — Verify endpoint (teacher)

**Files:**
- Modify: `nss-evidence-server/app.py` — add `GET /runs/{id}/verify`
- Modify: `nss-evidence-server/test_app.py`

- [ ] **Step 1: Write failing test for verify happy path**

Add to `test_app.py`:
```python
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
        json={"final_report_markdown": "# report", "files": []},
    )

    response = client.get(f"/runs/{run['run_id']}/verify")

    assert response.status_code == 200
    body = response.json()
    assert body["signature_valid"] is True
    assert body["verify_status"] == "verified"
```

- [ ] **Step 2: Write failing test for verify with tampered DB**

Add to `test_app.py`:
```python
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
        json={"final_report_markdown": "# report", "files": []},
    )

    # Tamper with DB directly
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
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `cd nss-evidence-server && .venv/bin/pytest test_app.py::test_verify_confirms_valid_signature test_app.py::test_verify_detects_tampered_signature -v`
Expected: FAIL (404)

- [ ] **Step 4: Implement verify endpoint**

Add to `app.py`:
```python
@app.get("/runs/{run_id}/verify")
def verify_run(run_id: str) -> Dict[str, Any]:
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
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `cd nss-evidence-server && .venv/bin/pytest test_app.py::test_verify_confirms_valid_signature test_app.py::test_verify_detects_tampered_signature -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add nss-evidence-server/app.py nss-evidence-server/test_app.py
git commit -m "feat(evidence): add GET /runs/{id}/verify endpoint"
```

---

### Task 5: Backend — Soft-delete endpoint

**Files:**
- Modify: `nss-evidence-server/app.py` — add `DELETE /runs/{id}`
- Modify: `nss-evidence-server/test_app.py`

- [ ] **Step 1: Write failing test**

Add to `test_app.py`:
```python
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd nss-evidence-server && .venv/bin/pytest test_app.py::test_delete_run_soft_deletes -v`
Expected: FAIL (405 Method Not Allowed)

- [ ] **Step 3: Implement delete endpoint**

Add to `app.py`:
```python
@app.delete("/runs/{run_id}")
def delete_run(run_id: str) -> Dict[str, str]:
    with connect() as conn:
        row = conn.execute("SELECT run_id FROM runs WHERE run_id = ?", (run_id,)).fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="run not found")
        conn.execute("UPDATE runs SET status = 'deleted' WHERE run_id = ?", (run_id,))
        conn.commit()
    return {"run_id": run_id, "status": "deleted"}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd nss-evidence-server && .venv/bin/pytest test_app.py::test_delete_run_soft_deletes -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add nss-evidence-server/app.py nss-evidence-server/test_app.py
git commit -m "feat(evidence): add soft-delete endpoint"
```

---

### Task 6: Backend — Update list_runs with status filter + dashboard badges

**Files:**
- Modify: `nss-evidence-server/app.py` — update `list_runs` to accept `?status=` query param, update dashboard HTML

- [ ] **Step 1: Write failing test for status filter**

Add to `test_app.py`:
```python
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
    client.post("/runs/start", json=payload)  # supersedes first

    response_active = client.get("/api/runs?status=active")
    response_all = client.get("/api/runs?status=all")

    assert len(response_active.json()["runs"]) == 1
    assert len(response_all.json()["runs"]) == 2
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd nss-evidence-server && .venv/bin/pytest test_app.py::test_list_runs_filters_by_status -v`
Expected: FAIL (returns both runs regardless of param)

- [ ] **Step 3: Update list_runs with status filter**

Replace `list_runs` in `app.py`:
```python
@app.get("/api/runs")
def list_runs(status: str = "active") -> Dict[str, Any]:
    with connect() as conn:
        if status == "all":
            rows = conn.execute(
                """
                SELECT run_id, student_name, student_id, exercise_id,
                       server_started_at, server_submitted_at, evidence_hash,
                       signature, status, verify_status
                FROM runs
                ORDER BY COALESCE(server_submitted_at, server_started_at) DESC
                """
            ).fetchall()
        else:
            rows = conn.execute(
                """
                SELECT run_id, student_name, student_id, exercise_id,
                       server_started_at, server_submitted_at, evidence_hash,
                       signature, status, verify_status
                FROM runs
                WHERE status = ?
                ORDER BY COALESCE(server_submitted_at, server_started_at) DESC
                """,
                (status,),
            ).fetchall()
    return {"runs": [dict(row) for row in rows]}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd nss-evidence-server && .venv/bin/pytest test_app.py::test_list_runs_filters_by_status -v`
Expected: PASS

- [ ] **Step 5: Update dashboard HTML with badges and status filter**

Replace the dashboard JS/table section in `homepage()` to show badges and add a status dropdown. The key changes to the `<script>` block:
- Add status select dropdown to toolbar
- Map `verify_status` to badges: `verified` → `✅已验证`, `null` + has signature never (finalize = verified), `null` + no signature → `📝待提交`
- Status column shows `superseded` / `deleted` badge if not active
- Verify button per row calls `/runs/{id}/verify` and shows result inline

(Full HTML replacement provided in implementation — too large for plan, but the logic is: badge function based on `verify_status` + `signature` + `status` fields, status dropdown sends `?status=` param to `/api/runs`)

- [ ] **Step 6: Run all backend tests**

Run: `cd nss-evidence-server && .venv/bin/pytest -v`
Expected: ALL PASS

- [ ] **Step 7: Commit**

```bash
git add nss-evidence-server/app.py nss-evidence-server/test_app.py
git commit -m "feat(evidence): status filter + dashboard badges"
```

---

### Task 7: nsscli — Split report flow (no upload, only skeleton)

**Files:**
- Modify: `nss-cli-agent/packages/opencode/src/cli/cmd/tui/component/lab-evidence.ts` — add `writeReportSkeleton()`
- Modify: `nss-cli-agent/packages/opencode/src/cli/cmd/tui/app.tsx:674-708` — rewrite `onReport`

- [ ] **Step 1: Add writeReportSkeleton function to lab-evidence.ts**

Add after `writeSignedReportDraft`:
```typescript
export async function writeReportSkeleton(input: {
  dir: string
  title: string
  meta: EvidenceMeta
}) {
  const content = `# 实验报告：${input.title}

## 基本信息

- 姓名：${input.meta.student.name}
- 学号：${input.meta.student.id}
- 实验开始时间：${input.meta.serverStartedAt}
- 提交编号：${input.meta.runId}

## 实验目标

请根据 README.md 补充本实验目标。

## 操作时间线

请记录关键操作步骤和时间。

## 代码文件清单

完成实验后执行 submit 自动生成。

## 实现要点（从抽象到代码的映射）

请根据你的实现补充关键思路、参数选择和代码映射。

## 遇到的问题与解决

请补充实验过程中遇到的问题和解决过程。

## 结论与反思

请补充实验结论和个人反思。
`
  const { writeFile } = await import("fs/promises")
  const { join } = await import("path")
  await writeFile(join(input.dir, "report.md"), content, "utf-8")
  return content
}
```

- [ ] **Step 2: Rewrite onReport in app.tsx (no upload, only start + skeleton)**

Replace the `onReport` handler (lines 674-708) with:
```typescript
onReport={async (sel) => {
  const cwd = process.env.PWD || process.cwd()
  const dir = getLessonDir(cwd, sel)
  let meta = await loadEvidenceMeta(cwd, sel)
  if (meta) {
    toast.show({ title: "已有报告", message: "该实验已初始化报告，请直接编辑后 submit", variant: "info" })
    return
  }
  const input = await DialogPrompt.show(dialog, "学生信息", {
    placeholder: "请输入姓名和学号，例如：张三 20240001",
  })
  if (!input) return
  const student = parseStudentInfo(input)
  if (!student) {
    toast.show({ title: "格式错误", message: "请输入：姓名 学号", variant: "warning" })
    return
  }
  try {
    meta = await startEvidenceRun(cwd, sel, student)
    await writeReportSkeleton({ dir, title: sel.title, meta })
    toast.show({ title: "报告骨架已生成", message: `${shortenHome(dir)}/report.md — 写完实验后选 submit 提交`, variant: "success" })
  } catch (err) {
    toast.error(err)
  }
}}
```

- [ ] **Step 3: Update imports in app.tsx**

Replace the lab-evidence import block with:
```typescript
import {
  collectFileEvidence,
  evidenceAppendix,
  loadEvidenceMeta,
  parseStudentInfo,
  startEvidenceRun,
  finalizeEvidence,
  writeReportSkeleton,
} from "@tui/component/lab-evidence"
```

- [ ] **Step 4: Typecheck**

Run: `cd nss-cli-agent/packages/opencode && npx tsc --noEmit --pretty false 2>&1`
Expected: no errors (may need to add `finalizeEvidence` in next task first — if type error, proceed to Task 8 then come back)

- [ ] **Step 5: Commit**

```bash
git add nss-cli-agent/packages/opencode/src/cli/cmd/tui/component/lab-evidence.ts nss-cli-agent/packages/opencode/src/cli/cmd/tui/app.tsx
git commit -m "feat(lesson): report only writes skeleton, no upload"
```

---

### Task 8: nsscli — Add submit action (finalize + write signature)

**Files:**
- Modify: `nss-cli-agent/packages/opencode/src/cli/cmd/tui/component/lab-evidence.ts` — add `finalizeEvidence()`
- Modify: `nss-cli-agent/packages/opencode/src/cli/cmd/tui/component/dialog-lesson-actions.tsx` — add submit option
- Modify: `nss-cli-agent/packages/opencode/src/cli/cmd/tui/app.tsx` — add `onSubmit` handler

- [ ] **Step 1: Add finalizeEvidence function to lab-evidence.ts**

Add after `submitEvidence`:
```typescript
export interface FinalizeResult {
  run_id: string
  server_submitted_at: string
  evidence_hash: string
  signature: string
}

export async function finalizeEvidence(meta: EvidenceMeta, reportMarkdown: string, files: EvidenceFileInfo[]): Promise<FinalizeResult> {
  const response = await fetch(`${meta.evidenceServer}/runs/${meta.runId}/finalize`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ final_report_markdown: reportMarkdown, files }),
  })
  if (!response.ok) {
    const text = await response.text()
    throw new Error(`定版失败：${response.status} ${text}`)
  }
  return (await response.json()) as FinalizeResult
}
```

- [ ] **Step 2: Update dialog-lesson-actions.tsx to add submit option**

Replace entire file:
```tsx
import { DialogSelect } from "@tui/ui/dialog-select"
import { useDialog } from "@tui/ui/dialog"
import { useLesson, type SelectedLesson } from "./use-lesson"

interface Props {
  onInit: (sel: SelectedLesson) => void
  onReport: (sel: SelectedLesson) => void
  onSubmit: (sel: SelectedLesson) => void
}

export function DialogLessonActions(props: Props) {
  const dialog = useDialog()
  const lesson = useLesson()
  const sel = lesson.selected()!

  const options = [
    { title: "init", value: "init" as const, description: "初始化实验：创建实验文件夹和 README" },
    { title: "report", value: "report" as const, description: "开始报告：记录学生信息，生成报告骨架" },
    { title: "submit", value: "submit" as const, description: "提交定版：采集文件哈希，上传报告并签名" },
  ]

  return (
    <DialogSelect
      title={`${sel.title}`}
      options={options}
      onSelect={(opt) => {
        dialog.clear()
        switch (opt.value) {
          case "init":
            props.onInit(sel)
            break
          case "report":
            props.onReport(sel)
            break
          case "submit":
            props.onSubmit(sel)
            break
        }
      }}
    />
  )
}
```

- [ ] **Step 3: Add onSubmit handler in app.tsx**

After the `onReport` handler closing `}}`, add:
```typescript
onSubmit={async (sel) => {
  const cwd = process.env.PWD || process.cwd()
  const dir = getLessonDir(cwd, sel)
  const meta = await loadEvidenceMeta(cwd, sel)
  if (!meta) {
    toast.show({ title: "请先 report", message: "该实验尚未初始化报告，请先选择 report", variant: "warning" })
    return
  }
  try {
    const { readFile, writeFile } = await import("fs/promises")
    const { join } = await import("path")
    const reportPath = join(dir, "report.md")
    let reportMd: string
    try {
      reportMd = await readFile(reportPath, "utf-8")
    } catch {
      toast.show({ title: "未找到报告", message: "请先编写 report.md", variant: "warning" })
      return
    }
    const files = await collectFileEvidence(dir)
    const result = await finalizeEvidence(meta, reportMd, files)
    const appendix = evidenceAppendix(result)
    const finalContent = reportMd.replace(/\n## 服务器证据签名[\s\S]*$/, "") + appendix
    await writeFile(reportPath, finalContent, "utf-8")
    toast.show({ title: "✅ 提交成功", message: `已定版并签名 — ${result.signature.slice(0, 16)}...`, variant: "success" })
  } catch (err) {
    toast.error(err)
  }
}}
```

- [ ] **Step 4: Typecheck**

Run: `cd nss-cli-agent/packages/opencode && npx tsc --noEmit --pretty false 2>&1`
Expected: no errors

- [ ] **Step 5: Build**

Run: `cd nss-cli-agent/packages/opencode && bun run script/build.ts --single`
Expected: build succeeds

- [ ] **Step 6: Commit**

```bash
git add nss-cli-agent/packages/opencode/src/cli/cmd/tui/component/lab-evidence.ts nss-cli-agent/packages/opencode/src/cli/cmd/tui/component/dialog-lesson-actions.tsx nss-cli-agent/packages/opencode/src/cli/cmd/tui/app.tsx
git commit -m "feat(lesson): add submit action with finalize + signature"
```

---

### Task 9: Backend — Update dashboard HTML with badges + verify button + status filter

**Files:**
- Modify: `nss-evidence-server/app.py` — replace homepage HTML

- [ ] **Step 1: Replace dashboard HTML**

Replace the entire `homepage()` function body with updated HTML that includes:
- Status filter dropdown (`active` / `all` / `superseded` / `deleted`)
- Badge rendering: `verify_status === 'verified'` → green ✅已验证; no signature → gray 📝待提交; status `superseded` → orange badge; status `deleted` → red badge
- Per-row "验证" button that calls `GET /runs/{id}/verify` and shows inline result
- Stats cards updated to count by verify_status

(Implementation: full HTML in Task 9 execution — structure same as current with added dropdown, badge function, and verify fetch call.)

- [ ] **Step 2: Run homepage test**

Run: `cd nss-evidence-server && .venv/bin/pytest test_app.py::test_homepage_serves_teacher_dashboard -v`
Expected: PASS (still contains "NSS Evidence Console")

- [ ] **Step 3: Run full backend test suite**

Run: `cd nss-evidence-server && .venv/bin/pytest -v`
Expected: ALL PASS

- [ ] **Step 4: Commit**

```bash
git add nss-evidence-server/app.py
git commit -m "feat(dashboard): badges, status filter, verify button"
```

---

### Task 10: Integration verification + cleanup

**Files:**
- No new files. Remove unused exports from `lab-evidence.ts` if any.

- [ ] **Step 1: Remove old submitEvidence from app.tsx imports if unused**

Check if `submitEvidence` is still referenced in app.tsx. If not, remove from import block. Also remove `writeSignedReportDraft` if unused (replaced by `writeReportSkeleton`).

- [ ] **Step 2: Typecheck**

Run: `cd nss-cli-agent/packages/opencode && npx tsc --noEmit --pretty false 2>&1`
Expected: no errors

- [ ] **Step 3: Build nsscli**

Run: `cd nss-cli-agent/packages/opencode && bun run script/build.ts --single`
Expected: build succeeds

- [ ] **Step 4: Run all backend tests**

Run: `cd nss-evidence-server && .venv/bin/pytest -v`
Expected: ALL PASS

- [ ] **Step 5: Manual smoke test**

1. Start server: `cd nss-evidence-server && NSS_EVIDENCE_SECRET=test-secret .venv/bin/uvicorn app:app --port 8000`
2. Open browser: `http://127.0.0.1:8000` → see dashboard with status filter + badges
3. Run nsscli → `/lesson` → select exercise → init → report → write some code → submit
4. Dashboard shows ✅已验证 for the submission
5. Click "验证" → shows signature_valid: true

- [ ] **Step 6: Final commit + push**

```bash
git add -A
git commit -m "chore: cleanup unused imports after report/submit split"
git push
```
