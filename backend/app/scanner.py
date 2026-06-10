import hashlib
import logging
import os
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from sqlite3 import Connection

from .db import connect
from .processing import ProcessedImage, process_image

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".heic", ".heif"}
EXCLUDED_DIRS = {"_rejects", ".siftr-cache"}
MAX_IMAGES = 2000

CACHE_ROOT = Path.home() / ".siftr"

logger = logging.getLogger(__name__)


def cache_dir_for(folder: Path) -> Path:
    digest = hashlib.sha1(str(folder).encode()).hexdigest()[:16]
    return CACHE_ROOT / digest


def open_cache(folder: Path) -> Connection:
    return connect(cache_dir_for(folder) / "siftr.db")


def find_images(folder: Path, recursive: bool = True) -> list[Path]:
    pattern = "**/*" if recursive else "*"
    images = [
        p
        for p in sorted(folder.glob(pattern))
        if p.is_file()
        and p.suffix.lower() in IMAGE_EXTENSIONS
        and not _in_excluded_dir(p, folder)
    ]
    return images[:MAX_IMAGES]


def _in_excluded_dir(path: Path, root: Path) -> bool:
    parents = path.relative_to(root).parts[:-1]
    return any(part in EXCLUDED_DIRS for part in parents)


def scan_folder(folder: Path, conn: Connection, recursive: bool = True) -> int:
    thumbs_dir = cache_dir_for(folder) / "thumbs"
    images = find_images(folder, recursive)

    entries: list[tuple[Path, os.stat_result]] = []
    for path in images:
        try:
            entries.append((path, path.stat()))
        except OSError:
            logger.warning("Skipping file that vanished mid-scan: %s", path)

    to_process: list[tuple[Path, os.stat_result]] = []
    for path, stat in entries:
        row = conn.execute(
            "SELECT mtime, size FROM photos WHERE path = ?", (str(path),)
        ).fetchone()
        fresh = (
            row is not None
            and row["mtime"] == stat.st_mtime
            and row["size"] == stat.st_size
        )
        if not fresh:
            to_process.append((path, stat))

    def safe_process(path: Path) -> ProcessedImage | None:
        try:
            return process_image(path, _thumb_path_for(thumbs_dir, path))
        except Exception:
            logger.warning(
                "Skipping unreadable image: %s", path, exc_info=True
            )
            return None

    # Decoding and hashing are CPU/IO heavy and release the GIL, so a thread
    # pool gives a large speedup; SQLite writes stay on this thread.
    failed: list[str] = []
    with ThreadPoolExecutor(max_workers=os.cpu_count()) as pool:
        results = pool.map(safe_process, (path for path, _ in to_process))
        for (path, stat), info in zip(to_process, results):
            if info is None:
                failed.append(str(path))
                continue
            conn.execute(
                """
                INSERT INTO photos (path, mtime, size, width, height, taken_at,
                                    phash, sharpness, face_count,
                                    face_sharpness, thumb_path)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(path) DO UPDATE SET
                    mtime = excluded.mtime, size = excluded.size,
                    width = excluded.width, height = excluded.height,
                    taken_at = excluded.taken_at, phash = excluded.phash,
                    sharpness = excluded.sharpness,
                    face_count = excluded.face_count,
                    face_sharpness = excluded.face_sharpness,
                    thumb_path = excluded.thumb_path
                """,
                (
                    str(path),
                    stat.st_mtime,
                    stat.st_size,
                    info.width,
                    info.height,
                    info.taken_at,
                    info.phash,
                    info.sharpness,
                    info.face_count,
                    info.face_sharpness,
                    str(_thumb_path_for(thumbs_dir, path)),
                ),
            )

    current_paths = [str(path) for path, _ in entries]
    placeholders = ",".join("?" * len(current_paths)) or "''"
    conn.execute(
        f"DELETE FROM photos WHERE path NOT IN ({placeholders})", current_paths
    )
    if failed:
        conn.executemany(
            "DELETE FROM photos WHERE path = ?", [(path,) for path in failed]
        )
    conn.commit()

    return conn.execute("SELECT COUNT(*) FROM photos").fetchone()[0]


def _thumb_path_for(thumbs_dir: Path, path: Path) -> Path:
    return thumbs_dir / f"{hashlib.sha1(str(path).encode()).hexdigest()}.jpg"
