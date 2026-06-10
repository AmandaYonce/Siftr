import threading
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import cv2
import imagehash
import numpy as np
from PIL import Image, ImageOps
from pillow_heif import register_heif_opener

register_heif_opener()

THUMBNAIL_EDGE = 320

# Laplacian variance grows with resolution, so sharpness is always measured
# at a fixed working size to keep scores comparable across differently
# sized images.
SHARPNESS_EDGE = 1024

_FACE_MIN_SIZE = (48, 48)

_thread_local = threading.local()

_EXIF_DATETIME_ORIGINAL = 36867
_EXIF_DATETIME = 306
_EXIF_IFD = 0x8769


@dataclass
class ProcessedImage:
    width: int
    height: int
    taken_at: str | None
    phash: str
    sharpness: float
    face_count: int
    face_sharpness: float


def process_image(path: Path, thumb_path: Path) -> ProcessedImage:
    with Image.open(path) as img:
        taken_at = _read_taken_at(img)
        img = ImageOps.exif_transpose(img)
        width, height = img.size
        phash = str(imagehash.phash(img))
        rgb = img.convert("RGB")
        gray = _working_gray(rgb)
        sharpness = float(cv2.Laplacian(gray, cv2.CV_64F).var())
        face_count, face_sharpness = _face_metrics(gray)
        rgb.thumbnail((THUMBNAIL_EDGE, THUMBNAIL_EDGE))
        thumb_path.parent.mkdir(parents=True, exist_ok=True)
        rgb.save(thumb_path, "JPEG", quality=80)
    return ProcessedImage(
        width,
        height,
        taken_at,
        phash,
        sharpness,
        face_count,
        face_sharpness,
    )


def _working_gray(img: Image.Image) -> np.ndarray:
    gray = img.convert("L")
    if max(gray.size) > SHARPNESS_EDGE:
        gray.thumbnail((SHARPNESS_EDGE, SHARPNESS_EDGE))
    return np.asarray(gray)


def _face_metrics(gray: np.ndarray) -> tuple[int, float]:
    """Count frontal faces and score the sharpest face region.

    The frontal cascade only fires on faces turned toward the camera,
    so these metrics double as a looking-at-camera signal.
    """
    faces = _face_detector().detectMultiScale(
        gray, scaleFactor=1.1, minNeighbors=5, minSize=_FACE_MIN_SIZE
    )
    sharpest = 0.0
    for x, y, w, h in faces:
        region = gray[y:y + h, x:x + w]
        variance = float(cv2.Laplacian(region, cv2.CV_64F).var())
        sharpest = max(sharpest, variance)
    return len(faces), sharpest


def _face_detector() -> cv2.CascadeClassifier:
    # CascadeClassifier is not thread-safe; each scanner thread gets its
    # own instance.
    detector = getattr(_thread_local, "face_detector", None)
    if detector is None:
        cascade = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
        detector = cv2.CascadeClassifier(cascade)
        _thread_local.face_detector = detector
    return detector


def _read_taken_at(img: Image.Image) -> str | None:
    exif = img.getexif()
    raw = exif.get_ifd(_EXIF_IFD).get(_EXIF_DATETIME_ORIGINAL)
    if not raw:
        raw = exif.get(_EXIF_DATETIME)
    if not raw:
        return None
    try:
        return datetime.strptime(str(raw), "%Y:%m:%d %H:%M:%S").isoformat()
    except ValueError:
        return None
