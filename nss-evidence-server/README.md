# NSS Evidence Server

Minimal backend for NSS CLI lab evidence submission.

## What It Does

- Starts an experiment run and records server time.
- Accepts a report evidence package from `nsscli`.
- Stores evidence in SQLite.
- Returns an HMAC signature over `run_id + evidence_hash + server_submitted_at`.
- Lets teachers query the stored evidence by `run_id`.

Students can edit local `report.md`, but they cannot forge a matching server-side evidence record and signature without the server secret.

## Run Locally

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
NSS_EVIDENCE_SECRET=change-me .venv/bin/uvicorn app:app --host 127.0.0.1 --port 8000
```

## API

### Start Run

```bash
curl -s http://127.0.0.1:8000/runs/start \
  -H 'content-type: application/json' \
  -d '{
    "student_name":"张三",
    "student_id":"20240001",
    "exercise_id":"01-crypto-basic",
    "computer":{"os":"macOS","cpu":"Apple M1"}
  }'
```

### Submit Evidence

```bash
curl -s http://127.0.0.1:8000/runs/<run_id>/submit \
  -H 'content-type: application/json' \
  -d '{
    "report_markdown":"# report",
    "timeline":[{"time":"2026-06-08T12:00:00Z","event":"created solution.py"}],
    "files":[{"path":"solution.py","sha256":"abc","size":123}]
  }'
```

### Query Evidence

```bash
curl -s http://127.0.0.1:8000/runs/<run_id>
```

## Test

```bash
.venv/bin/pytest -q
```
