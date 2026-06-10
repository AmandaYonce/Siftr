import hashlib
from pathlib import Path

import pytest

from app import mover


@pytest.fixture
def folder(tmp_path: Path) -> Path:
    root = tmp_path / "photos"
    root.mkdir()
    (root / "a.jpg").write_bytes(b"photo-a")
    (root / "b.jpg").write_bytes(b"photo-b")
    (root / "c.jpg").write_bytes(b"photo-c")
    return root


def _content_hashes(root: Path) -> set[str]:
    return {
        hashlib.sha1(p.read_bytes()).hexdigest()
        for p in root.rglob("*")
        if p.is_file()
    }


def test_apply_moves_files_and_never_deletes(folder: Path):
    before = _content_hashes(folder)

    moves = mover.apply_rejects(
        folder, [(1, folder / "a.jpg"), (2, folder / "b.jpg")]
    )

    assert len(moves) == 2
    assert not (folder / "a.jpg").exists()
    assert (folder / "_rejects" / "a.jpg").read_bytes() == b"photo-a"
    assert (folder / "_rejects" / "b.jpg").read_bytes() == b"photo-b"
    assert _content_hashes(folder) == before


def test_apply_suffixes_on_name_collision(folder: Path):
    rejects = folder / "_rejects"
    rejects.mkdir()
    (rejects / "a.jpg").write_bytes(b"earlier-reject")

    moves = mover.apply_rejects(folder, [(1, folder / "a.jpg")])

    assert moves[0].destination.name == "a-1.jpg"
    assert (rejects / "a.jpg").read_bytes() == b"earlier-reject"
    assert (rejects / "a-1.jpg").read_bytes() == b"photo-a"


def test_outside_path_aborts_the_whole_batch_untouched(
    folder: Path, tmp_path: Path
):
    outside = tmp_path / "outside.jpg"
    outside.write_bytes(b"do not touch")

    with pytest.raises(ValueError):
        mover.apply_rejects(folder, [(1, folder / "a.jpg"), (2, outside)])

    assert outside.exists()
    assert (folder / "a.jpg").read_bytes() == b"photo-a"
    assert not (folder / "_rejects").exists()


def test_apply_skips_already_moved_files(folder: Path):
    mover.apply_rejects(folder, [(1, folder / "a.jpg")])
    moves = mover.apply_rejects(folder, [(1, folder / "a.jpg")])
    assert moves == []
    assert (folder / "_rejects" / "a.jpg").read_bytes() == b"photo-a"


def test_undo_restores_files_to_original_paths(folder: Path):
    before = _content_hashes(folder)
    moves = mover.apply_rejects(
        folder, [(1, folder / "a.jpg"), (2, folder / "b.jpg")]
    )

    restored = mover.undo_moves(moves)

    assert restored == 2
    assert (folder / "a.jpg").read_bytes() == b"photo-a"
    assert (folder / "b.jpg").read_bytes() == b"photo-b"
    assert _content_hashes(folder) == before


def test_undo_never_overwrites_a_new_file(folder: Path):
    moves = mover.apply_rejects(folder, [(1, folder / "a.jpg")])
    (folder / "a.jpg").write_bytes(b"new occupant")

    restored = mover.undo_moves(moves)

    assert restored == 1
    assert (folder / "a.jpg").read_bytes() == b"new occupant"
    assert (folder / "a-1.jpg").read_bytes() == b"photo-a"
