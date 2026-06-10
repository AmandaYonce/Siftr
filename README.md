# Siftr

Point Siftr at a folder of photos and it finds near-duplicate clusters (burst
shots, slight edits), scores each shot for sharpness, and gives you a fast
keyboard-driven UI to keep the best and sweep the rest aside — without ever
deleting an original.

> **Non-destructive guarantee:** Siftr never deletes photos. Rejected files
> are moved into a `_rejects/` subfolder and can always be restored with Undo.

## Quickstart

```bash
# Backend (Python 3.11+)
cd backend
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/uvicorn app.main:app --reload --port 8000

# Frontend (in a second terminal)
cd frontend
npm install
npm run dev
```

Open http://localhost:5173 — the Vite dev server proxies `/api` to the backend.

## Status

Under active development. Algorithm details, screenshots, and design notes
will land here as the build progresses.
