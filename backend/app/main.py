import time
from pathlib import Path
from sqlite3 import Connection

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse

from . import scanner
from .clustering import cluster_by_hamming
from .schemas import (
    ClusterOut,
    ClustersResponse,
    PhotoOut,
    ScanRequest,
    ScanResponse,
    Summary,
)

app = FastAPI(title="Siftr")

state: dict[str, Path | None] = {"folder": None}


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    return JSONResponse(status_code=exc.status_code, content={"error": exc.detail})


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/api/scan")
def scan(req: ScanRequest) -> ScanResponse:
    folder = _validate_folder(req.folder)
    start = time.monotonic()
    conn = scanner.open_cache(folder)
    try:
        try:
            photo_count = scanner.scan_folder(folder, conn, req.recursive)
        except PermissionError:
            raise HTTPException(403, f"Permission denied reading: {folder}")
        if photo_count == 0:
            raise HTTPException(422, f"No images found in: {folder}")
        clusters = _build_clusters(conn, req.threshold)
    finally:
        conn.close()
    state["folder"] = folder
    duration_ms = int((time.monotonic() - start) * 1000)
    return ScanResponse(
        photo_count=photo_count,
        cluster_count=len(clusters.clusters),
        duration_ms=duration_ms,
    )


@app.get("/api/clusters")
def clusters(threshold: int = 9) -> ClustersResponse:
    conn = _open_current_cache()
    try:
        return _build_clusters(conn, threshold)
    finally:
        conn.close()


@app.get("/api/thumbnail/{photo_id}")
def thumbnail(photo_id: int) -> FileResponse:
    conn = _open_current_cache()
    try:
        row = conn.execute(
            "SELECT thumb_path FROM photos WHERE id = ?", (photo_id,)
        ).fetchone()
    finally:
        conn.close()
    if row is None or not Path(row["thumb_path"]).exists():
        raise HTTPException(404, f"No thumbnail for photo {photo_id}")
    return FileResponse(row["thumb_path"], media_type="image/jpeg")


def _validate_folder(raw: str) -> Path:
    folder = Path(raw).expanduser()
    if not folder.exists():
        raise HTTPException(404, f"Folder not found: {folder}")
    if not folder.is_dir():
        raise HTTPException(422, f"Not a directory: {folder}")
    return folder.resolve()


def _open_current_cache() -> Connection:
    folder = state["folder"]
    if folder is None:
        raise HTTPException(409, "No folder scanned yet")
    return scanner.open_cache(folder)


def _build_clusters(conn: Connection, threshold: int) -> ClustersResponse:
    rows = conn.execute("SELECT * FROM photos").fetchall()
    by_id = {row["id"]: row for row in rows}
    groups = cluster_by_hamming({r["id"]: r["phash"] for r in rows}, threshold)

    # Multi-photo clusters first (they need review), each photo sharpest-first.
    groups.sort(key=lambda g: (-len(g), min(by_id[i]["path"] for i in g)))

    cluster_models = []
    duplicates = 0
    reclaimable = 0
    for index, group in enumerate(groups, start=1):
        photos = sorted(group, key=lambda i: -by_id[i]["sharpness"])
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
    )
