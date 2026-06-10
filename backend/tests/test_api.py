from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from PIL import Image

from app import main, scanner
from app.main import app


@pytest.fixture
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setattr(scanner, "CACHE_ROOT", tmp_path / "cache")
    monkeypatch.setattr(main, "session", main.Session())
    return TestClient(app)


@pytest.fixture
def photo_folder(tmp_path: Path) -> Path:
    folder = tmp_path / "photos"
    folder.mkdir()
    for name, seed in [("a.jpg", 10), ("b.jpg", 10), ("c.jpg", 200)]:
        img = Image.new("RGB", (64, 64))
        pixels = [
            (seed, (x * y) % 256, (x + y + seed) % 256)
            for x in range(64)
            for y in range(64)
        ]
        img.putdata(pixels)
        img.save(folder / name)
    return folder


def test_decisions_require_a_scan_first(client: TestClient):
    res = client.post("/api/decisions", json={"reject": [1]})
    assert res.status_code == 409
    assert "error" in res.json()


def test_decisions_roundtrip(client: TestClient, photo_folder: Path):
    res = client.post("/api/scan", json={"folder": str(photo_folder)})
    assert res.status_code == 200

    res = client.post("/api/decisions", json={"reject": [1, 3]})
    assert res.json() == {"ok": True}
    assert main.session.rejected == {1, 3}


def test_apply_and_undo_roundtrip(client: TestClient, photo_folder: Path):
    res = client.post("/api/scan", json={"folder": str(photo_folder)})
    assert res.status_code == 200

    conn_rows = client.get("/api/clusters?threshold=8").json()
    a_photo = conn_rows["clusters"][0]["photos"][0]

    client.post("/api/decisions", json={"reject": [a_photo["id"]]})
    res = client.post("/api/apply")
    body = res.json()
    assert body["moved"] == 1
    assert body["reclaimedBytes"] > 0
    rejects = photo_folder / "_rejects"
    assert len(list(rejects.iterdir())) == 1

    res = client.post("/api/undo")
    assert res.json() == {"restored": 1}
    assert list(rejects.iterdir()) == []
    assert (photo_folder / a_photo["filename"]).exists()


def test_apply_without_rejects_is_an_error(
    client: TestClient, photo_folder: Path
):
    client.post("/api/scan", json={"folder": str(photo_folder)})
    assert client.post("/api/apply").status_code == 422
    assert client.post("/api/undo").status_code == 409


def test_second_apply_requires_undo_or_rescan(
    client: TestClient, photo_folder: Path
):
    client.post("/api/scan", json={"folder": str(photo_folder)})
    photo = client.get("/api/clusters").json()["clusters"][0]["photos"][0]
    client.post("/api/decisions", json={"reject": [photo["id"]]})
    assert client.post("/api/apply").status_code == 200

    client.post("/api/decisions", json={"reject": [photo["id"]]})
    assert client.post("/api/apply").status_code == 409

    assert client.post("/api/undo").status_code == 200


def test_apply_with_stale_ids_is_an_error(
    client: TestClient, photo_folder: Path
):
    client.post("/api/scan", json={"folder": str(photo_folder)})
    client.post("/api/decisions", json={"reject": [99999]})
    res = client.post("/api/apply")
    assert res.status_code == 409
    assert "re-scan" in res.json()["error"]


def test_every_scan_starts_a_fresh_review(
    client: TestClient, photo_folder: Path
):
    client.post("/api/scan", json={"folder": str(photo_folder)})
    client.post("/api/decisions", json={"reject": [2]})

    client.post("/api/scan", json={"folder": str(photo_folder)})
    assert main.session.rejected == set()
