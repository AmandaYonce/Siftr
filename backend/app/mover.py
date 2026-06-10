import logging
import os
from dataclasses import dataclass
from itertools import count
from pathlib import Path

REJECTS_DIR_NAME = "_rejects"

logger = logging.getLogger(__name__)


@dataclass
class Move:
    photo_id: int
    source: Path
    destination: Path


def apply_rejects(folder: Path, photos: list[tuple[int, Path]]) -> list[Move]:
    """Move rejected photos into <folder>/_rejects.

    Every source path is validated before any file is touched, so an
    invalid path aborts the whole batch instead of leaving it half
    moved. Files are only ever moved, never deleted or overwritten.
    """
    root = folder.resolve()
    rejects_dir = root / REJECTS_DIR_NAME

    sources: list[tuple[int, Path]] = []
    for photo_id, source in photos:
        resolved = source.resolve()
        if not resolved.is_relative_to(root):
            raise ValueError(
                f"Refusing to move file outside folder: {source}"
            )
        if resolved.is_file():
            sources.append((photo_id, resolved))

    rejects_dir.mkdir(exist_ok=True)
    moves: list[Move] = []
    for photo_id, resolved in sources:
        try:
            destination = _move_no_clobber(
                resolved, rejects_dir / resolved.name
            )
        except OSError:
            logger.warning(
                "Could not move %s; leaving it in place",
                resolved,
                exc_info=True,
            )
            continue
        moves.append(Move(photo_id, resolved, destination))
    return moves


def undo_moves(moves: list[Move]) -> int:
    restored = 0
    for move in reversed(moves):
        if not move.destination.is_file():
            continue
        move.source.parent.mkdir(parents=True, exist_ok=True)
        try:
            _move_no_clobber(move.destination, move.source)
        except OSError:
            logger.warning(
                "Could not restore %s; it remains in %s",
                move.source,
                move.destination,
                exc_info=True,
            )
            continue
        restored += 1
    return restored


def _move_no_clobber(source: Path, wanted: Path) -> Path:
    """Move source to wanted (or a numbered sibling), never overwriting.

    A plain exists-then-move check can race with another writer, so the
    destination name is claimed first with an atomic O_CREAT|O_EXCL open
    (which also refuses to follow dangling symlinks); the file is then
    renamed onto its own placeholder.
    """
    for n in count(0):
        candidate = (
            wanted
            if n == 0
            else wanted.with_name(f"{wanted.stem}-{n}{wanted.suffix}")
        )
        try:
            fd = os.open(candidate, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        except FileExistsError:
            continue
        os.close(fd)
        try:
            os.replace(source, candidate)
        except OSError:
            os.unlink(candidate)
            raise
        return candidate
    raise AssertionError("unreachable")
