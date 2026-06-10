from pathlib import Path

from app.db import connect
from app.main import _build_clusters


def _insert(conn, photo_id, sharpness, face_count, face_sharpness):
    conn.execute(
        """
        INSERT INTO photos (id, path, mtime, size, width, height, taken_at,
                            phash, sharpness, face_count, face_sharpness,
                            thumb_path)
        VALUES (?, ?, 0, 100, 10, 10, NULL, ?, ?, ?, ?, 'thumb.jpg')
        """,
        (
            photo_id,
            f"/photos/p{photo_id}.jpg",
            "0" * 16,  # identical hashes: everything clusters together
            sharpness,
            face_count,
            face_sharpness,
        ),
    )


def test_default_ranking_prefers_overall_sharpness(tmp_path: Path):
    conn = connect(tmp_path / "cache.db")
    _insert(conn, 1, sharpness=900.0, face_count=0, face_sharpness=0.0)
    _insert(conn, 2, sharpness=500.0, face_count=1, face_sharpness=800.0)

    result = _build_clusters(conn, threshold=4, prefer_faces=False)
    assert result.clusters[0].suggested_keeper_id == 1
    conn.close()


def test_prefer_faces_picks_camera_facing_shot(tmp_path: Path):
    conn = connect(tmp_path / "cache.db")
    _insert(conn, 1, sharpness=900.0, face_count=0, face_sharpness=0.0)
    _insert(conn, 2, sharpness=500.0, face_count=1, face_sharpness=300.0)
    _insert(conn, 3, sharpness=400.0, face_count=2, face_sharpness=700.0)

    result = _build_clusters(conn, threshold=4, prefer_faces=True)
    photos = [p.id for p in result.clusters[0].photos]
    assert result.clusters[0].suggested_keeper_id == 3
    assert photos == [3, 2, 1]
    conn.close()


def test_prefer_faces_falls_back_to_sharpness_without_faces(tmp_path: Path):
    conn = connect(tmp_path / "cache.db")
    _insert(conn, 1, sharpness=300.0, face_count=0, face_sharpness=0.0)
    _insert(conn, 2, sharpness=700.0, face_count=0, face_sharpness=0.0)

    result = _build_clusters(conn, threshold=4, prefer_faces=True)
    assert result.clusters[0].suggested_keeper_id == 2
    conn.close()
