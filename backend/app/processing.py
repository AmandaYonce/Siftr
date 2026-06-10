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


def process_image(path: Path, thumb_path: Path) -> ProcessedImage:
    with Image.open(path) as img:
        taken_at = _read_taken_at(img)
        img = ImageOps.exif_transpose(img)
        width, height = img.size
        phash = str(imagehash.phash(img))
        rgb = img.convert("RGB")
        sharpness = _sharpness(rgb)
        rgb.thumbnail((THUMBNAIL_EDGE, THUMBNAIL_EDGE))
        thumb_path.parent.mkdir(parents=True, exist_ok=True)
        rgb.save(thumb_path, "JPEG", quality=80)
    return ProcessedImage(width, height, taken_at, phash, sharpness)


def _sharpness(img: Image.Image) -> float:
    gray = img.convert("L")
    if max(gray.size) > SHARPNESS_EDGE:
        gray.thumbnail((SHARPNESS_EDGE, SHARPNESS_EDGE))
    return float(cv2.Laplacian(np.asarray(gray), cv2.CV_64F).var())


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
