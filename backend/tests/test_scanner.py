from pathlib import Path

import pytest
from PIL import Image

from app import scanner


@pytest.fixture
def photo_folder(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setattr(scanner, "CACHE_ROOT", tmp_path / "cache")
    folder = tmp_path / "photos"
    folder.mkdir()
    _save_gradient(folder / "a.jpg", seed=10)
    _save_gradient(folder / "b.jpg", seed=10)
    _save_gradient(folder / "c.jpg", seed=200)
    (folder / "notes.txt").write_text("not an image")
    return folder


def _save_gradient(path: Path, seed: int) -> None:
    img = Image.new("RGB", (64, 64))
    pixels = [
        (seed, (x * y) % 256, (x + y + seed) % 256)
        for x in range(64)
        for y in range(64)
    ]
    img.putdata(pixels)
    img.save(path)


def test_scan_caches_results_and_skips_non_images(photo_folder: Path):
    conn = scanner.open_cache(photo_folder)
    count = scanner.scan_folder(photo_folder, conn)
    assert count == 3

    rows = conn.execute("SELECT * FROM photos ORDER BY path").fetchall()
    assert [Path(r["path"]).name for r in rows] == ["a.jpg", "b.jpg", "c.jpg"]
    for row in rows:
        assert len(row["phash"]) == 16
        assert row["sharpness"] >= 0
        assert Path(row["thumb_path"]).exists()
    conn.close()


def test_rescan_uses_cache_without_reprocessing(
    photo_folder: Path, monkeypatch: pytest.MonkeyPatch
):
    conn = scanner.open_cache(photo_folder)
    scanner.scan_folder(photo_folder, conn)

    def fail_if_called(*args, **kwargs):
        raise AssertionError("process_image should not run on a cached scan")

    monkeypatch.setattr(scanner, "process_image", fail_if_called)
    assert scanner.scan_folder(photo_folder, conn) == 3
    conn.close()


def test_scan_prunes_deleted_files(photo_folder: Path):
    conn = scanner.open_cache(photo_folder)
    scanner.scan_folder(photo_folder, conn)
    (photo_folder / "c.jpg").unlink()
    assert scanner.scan_folder(photo_folder, conn) == 2
    conn.close()


def test_corrupted_file_drops_its_stale_cache_row(photo_folder: Path):
    conn = scanner.open_cache(photo_folder)
    scanner.scan_folder(photo_folder, conn)

    corrupted = photo_folder / "c.jpg"
    corrupted.write_bytes(b"not a real jpeg")

    assert scanner.scan_folder(photo_folder, conn) == 2
    row = conn.execute(
        "SELECT 1 FROM photos WHERE path = ?", (str(corrupted),)
    ).fetchone()
    assert row is None
    conn.close()


def test_heic_files_are_scanned(photo_folder: Path):
    img = Image.new("RGB", (64, 64), color=(40, 160, 90))
    img.save(photo_folder / "phone.heic", format="HEIF")

    conn = scanner.open_cache(photo_folder)
    assert scanner.scan_folder(photo_folder, conn) == 4

    row = conn.execute(
        "SELECT phash, thumb_path FROM photos WHERE path LIKE '%phone.heic'"
    ).fetchone()
    assert row is not None
    assert len(row["phash"]) == 16
    assert Path(row["thumb_path"]).exists()
    conn.close()


def test_rejects_and_cache_dirs_are_excluded(photo_folder: Path):
    rejects = photo_folder / "_rejects"
    rejects.mkdir()
    _save_gradient(rejects / "rejected.jpg", seed=50)

    images = scanner.find_images(photo_folder)
    assert all("_rejects" not in p.parts for p in images)


def test_non_recursive_scan_ignores_subfolders(photo_folder: Path):
    sub = photo_folder / "edits"
    sub.mkdir()
    _save_gradient(sub / "edited.jpg", seed=99)

    assert len(scanner.find_images(photo_folder, recursive=True)) == 4
    assert len(scanner.find_images(photo_folder, recursive=False)) == 3
