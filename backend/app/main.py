import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from sqlite3 import Connection

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse

from . import mover, scanner
from .clustering import cluster_by_hamming
from .schemas import (
    ApplyResponse,
    ClusterOut,
    ClustersResponse,
    DecisionsRequest,
    PhotoOut,
    ScanRequest,
    ScanResponse,
    Summary,
    UndoResponse,
)

app = FastAPI(title="Siftr")


@dataclass
class Session:
    """Single-user, in-memory review session (a deliberate scope choice)."""

    folder: Path | None = None
    rejected: set[int] = field(default_factory=set)
    applied: list[mover.Move] = field(default_factory=list)


session = Session()

# Scans are serialized: sync endpoints run in a thread pool, so two
# concurrent scan requests could otherwise write the same SQLite file.
_scan_lock = threading.Lock()


@app.exception_handler(HTTPException)
async def http_exception_handler(
    request: Request, exc: HTTPException
) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code, content={"error": exc.detail}
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    first = exc.errors()[0] if exc.errors() else {}
    location = ".".join(str(part) for part in first.get("loc", []))
    message = first.get("msg", "Invalid request")
    return JSONResponse(
        status_code=422, content={"error": f"{location}: {message}"}
    )


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/api/scan")
def scan(req: ScanRequest) -> ScanResponse:
    folder = _validate_folder(req.folder)
    start = time.monotonic()
    with _scan_lock:
        conn = scanner.open_cache(folder)
        try:
            try:
                photo_count = scanner.scan_folder(
                    folder, conn, req.recursive
                )
            except PermissionError:
                raise HTTPException(
                    403, f"Permission denied reading: {folder}"
                )
            if photo_count == 0:
                raise HTTPException(422, f"No images found in: {folder}")
            clusters = _build_clusters(conn, req.threshold)
        finally:
            conn.close()
    session.folder = folder
    session.rejected = set()
    session.applied = []
    duration_ms = int((time.monotonic() - start) * 1000)
    return ScanResponse(
        photo_count=photo_count,
        cluster_count=len(clusters.clusters),
        duration_ms=duration_ms,
    )


@app.get("/api/clusters")
def clusters(
    threshold: int = Query(9, ge=0, le=64),
    prefer_faces: bool = Query(False, alias="preferFaces"),
) -> ClustersResponse:
    conn = _open_current_cache()
    try:
        return _build_clusters(conn, threshold, prefer_faces)
    finally:
        conn.close()


@app.post("/api/decisions")
def decisions(req: DecisionsRequest) -> dict[str, bool]:
    if session.folder is None:
        raise HTTPException(409, "No folder scanned yet")
    session.rejected = set(req.reject)
    return {"ok": True}


@app.post("/api/apply")
def apply() -> ApplyResponse:
    # The whole transaction holds the lock so a concurrent apply or scan
    # can neither double-move files nor clobber the undo history.
    with _scan_lock:
        if session.folder is None:
            raise HTTPException(409, "No folder scanned yet")
        if session.applied:
            raise HTTPException(
                409, "An apply is already awaiting undo; undo or re-scan"
            )
        if not session.rejected:
            raise HTTPException(422, "No photos are marked as rejected")

        conn = scanner.open_cache(session.folder)
        try:
            ids = sorted(session.rejected)
            placeholders = ",".join("?" * len(ids))
            rows = conn.execute(
                "SELECT id, path, size FROM photos"
                f" WHERE id IN ({placeholders})",
                ids,
            ).fetchall()
        finally:
            conn.close()
        if len(rows) != len(ids):
            raise HTTPException(
                409,
                "Some rejected photos are no longer in the scan;"
                " re-scan and review again",
            )

        photos = [(row["id"], Path(row["path"])) for row in rows]
        sizes = {row["id"]: row["size"] for row in rows}
        try:
            moves = mover.apply_rejects(session.folder, photos)
        except ValueError as exc:
            raise HTTPException(400, str(exc))

        session.applied = moves
        session.rejected = set()
    reclaimed = sum(sizes[move.photo_id] for move in moves)
    return ApplyResponse(moved=len(moves), reclaimed_bytes=reclaimed)


@app.post("/api/undo")
def undo() -> UndoResponse:
    with _scan_lock:
        if not session.applied:
            raise HTTPException(409, "Nothing to undo")
        restored = mover.undo_moves(session.applied)
        session.applied = []
    return UndoResponse(restored=restored)


@app.get("/api/thumbnail/{photo_id}")
def thumbnail(photo_id: int) -> FileResponse:
    conn = _open_current_cache()
    try:
        row = conn.execute(
            "SELECT thumb_path FROM photos WHERE id = ?", (photo_id,)
        ).fetchone()
    finally:
        conn.close()
    if row is None:
        raise HTTPException(404, f"No thumbnail for photo {photo_id}")
    thumb = Path(row["thumb_path"]).resolve()
    if not thumb.is_relative_to(scanner.CACHE_ROOT) or not thumb.exists():
        raise HTTPException(404, f"No thumbnail for photo {photo_id}")
    return FileResponse(thumb, media_type="image/jpeg")


def _validate_folder(raw: str) -> Path:
    folder = Path(raw).expanduser()
    if not folder.exists():
        raise HTTPException(404, f"Folder not found: {folder}")
    if not folder.is_dir():
        raise HTTPException(422, f"Not a directory: {folder}")
    return folder.resolve()


def _open_current_cache() -> Connection:
    if session.folder is None:
        raise HTTPException(409, "No folder scanned yet")
    return scanner.open_cache(session.folder)


def _build_clusters(
    conn: Connection, threshold: int, prefer_faces: bool = False
) -> ClustersResponse:
    rows = conn.execute("SELECT * FROM photos").fetchall()
    by_id = {row["id"]: row for row in rows}
    groups = cluster_by_hamming({r["id"]: r["phash"] for r in rows}, threshold)

    # Multi-photo clusters first (they need review), each photo best-first.
    groups.sort(key=lambda g: (-len(g), min(by_id[i]["path"] for i in g)))

    def rank(photo_id: int) -> tuple[float, ...]:
        row = by_id[photo_id]
        if prefer_faces:
            # Camera-facing shots first, sharpest face wins among them;
            # faceless photos fall back to overall sharpness.
            has_face = 1 if row["face_count"] > 0 else 0
            return (-has_face, -row["face_sharpness"], -row["sharpness"])
        return (-row["sharpness"],)

    cluster_models = []
    duplicates = 0
    reclaimable = 0
    for index, group in enumerate(groups, start=1):
        photos = sorted(group, key=rank)
        keeper_id = photos[0]
        if len(photos) > 1:
            duplicates += len(photos) - 1
            reclaimable += sum(by_id[i]["size"] for i in photos[1:])
        cluster_models.append(
            ClusterOut(
                id=f"c{index}",
                suggested_keeper_id=keeper_id,
                photos=[_photo_out(by_id[i]) for i in photos],
            )
        )

    summary = Summary(
        photos=len(rows),
        clusters=len(groups),
        duplicates=duplicates,
        reclaimable_bytes=reclaimable,
    )
    return ClustersResponse(summary=summary, clusters=cluster_models)


def _photo_out(row) -> PhotoOut:
    return PhotoOut(
        id=row["id"],
        filename=Path(row["path"]).name,
        thumbnail_url=f"/api/thumbnail/{row['id']}",
        sharpness=round(row["sharpness"], 1),
        width=row["width"],
        height=row["height"],
        taken_at=row["taken_at"],
        bytes=row["size"],
        face_count=row["face_count"],
    )
