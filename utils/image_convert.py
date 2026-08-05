"""Image conversion helpers (HEIC/HEIF → PNG, Frame TV aspect-ratio fit)."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import BinaryIO, Optional, Tuple, Union

logger = logging.getLogger(__name__)

HEIC_EXTENSIONS = frozenset({"heic", "heif"})

# Highest-quality format already supported by this app and Frame TV art mode.
OUTPUT_FORMAT = "PNG"
OUTPUT_EXTENSION = "png"

# Samsung Frame art mode is 16:9; non-matching images are stretched unless padded.
# 4K canvas scales cleanly on both 4K and 1080p Frames without distorting aspect ratio.
FRAME_TV_CANVAS_SIZE: Tuple[int, int] = (3840, 2160)
FRAME_TV_FILL_COLOR: Tuple[int, int, int] = (0, 0, 0)

_heif_registered = False


class ImageConvertError(Exception):
    """Raised when image conversion fails."""


def _ensure_heif_support() -> None:
    """Register HEIF openers with Pillow (idempotent)."""
    global _heif_registered
    if _heif_registered:
        return
    try:
        from pillow_heif import register_heif_opener

        register_heif_opener()
        _heif_registered = True
    except ImportError as e:
        raise ImageConvertError(
            "HEIC support is not available (pillow-heif is not installed)"
        ) from e


def is_heic_filename(filename: str) -> bool:
    if not filename or "." not in filename:
        return False
    return filename.rsplit(".", 1)[1].lower() in HEIC_EXTENSIONS


def heic_output_filename(filename: str) -> str:
    """Return the PNG filename to store after converting a HEIC upload."""
    stem = filename.rsplit(".", 1)[0]
    return f"{stem}.{OUTPUT_EXTENSION}"


def convert_heic_to_png(
    source: Union[str, Path, BinaryIO],
    dest_path: Union[str, Path],
) -> None:
    """
    Decode a HEIC/HEIF image and write a lossless PNG.

    Applies EXIF orientation so the stored image matches how it appears
    on phones / cameras.
    """
    try:
        from PIL import Image, ImageOps
    except ImportError as e:
        raise ImageConvertError("Pillow is not installed") from e

    _ensure_heif_support()

    dest_path = Path(dest_path)
    dest_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        with Image.open(source) as img:
            # Honor camera orientation tags common in phone HEIC photos
            img = ImageOps.exif_transpose(img) or img

            # PNG supports RGB/RGBA; normalize odd HEIC modes (e.g. P, CMYK)
            if img.mode not in ("RGB", "RGBA"):
                if img.mode in ("LA", "PA") or "A" in img.getbands():
                    img = img.convert("RGBA")
                else:
                    img = img.convert("RGB")

            # Lossless PNG — highest quality among app-supported formats
            img.save(
                dest_path,
                format=OUTPUT_FORMAT,
                optimize=True,
                compress_level=6,
            )
    except ImageConvertError:
        raise
    except Exception as e:
        logger.exception("HEIC conversion failed")
        raise ImageConvertError(f"Failed to convert HEIC image: {e}") from e


def fit_image_to_canvas(
    source_path: Union[str, Path],
    dest_path: Union[str, Path],
    canvas_size: Tuple[int, int] = FRAME_TV_CANVAS_SIZE,
    fill_color: Tuple[int, int, int] = FRAME_TV_FILL_COLOR,
    output_format: str = "JPEG",
    jpeg_quality: int = 95,
) -> Tuple[int, int]:
    """
    Scale an image to fit inside a fixed canvas without distortion.

    The image is resized with LANCZOS so the longer side fits the canvas,
    then centered on a solid background (letterbox / pillarbox). This is
    what Frame TVs need: they stretch non-16:9 art to fill the screen.

    Returns:
        (fitted_width, fitted_height) of the image content inside the canvas.
    """
    try:
        from PIL import Image, ImageOps
    except ImportError as e:
        raise ImageConvertError("Pillow is not installed") from e

    source_path = Path(source_path)
    dest_path = Path(dest_path)
    dest_path.parent.mkdir(parents=True, exist_ok=True)

    canvas_w, canvas_h = canvas_size
    if canvas_w <= 0 or canvas_h <= 0:
        raise ImageConvertError("Canvas size must be positive")

    try:
        with Image.open(source_path) as img:
            img = ImageOps.exif_transpose(img) or img
            # Flatten alpha onto the fill color so transparent PNGs look right
            if img.mode in ("RGBA", "LA") or (img.mode == "P" and "transparency" in img.info):
                rgba = img.convert("RGBA")
                background = Image.new("RGBA", rgba.size, (*fill_color, 255))
                background.paste(rgba, mask=rgba.split()[-1])
                img = background.convert("RGB")
            elif img.mode != "RGB":
                img = img.convert("RGB")

            # Shrink-or-grow to fit inside canvas while keeping aspect ratio
            fitted = ImageOps.contain(img, canvas_size, method=Image.Resampling.LANCZOS)

            canvas = Image.new("RGB", canvas_size, fill_color)
            offset = (
                (canvas_w - fitted.width) // 2,
                (canvas_h - fitted.height) // 2,
            )
            canvas.paste(fitted, offset)

            save_kwargs = {}
            fmt = output_format.upper()
            if fmt in ("JPEG", "JPG"):
                save_kwargs["quality"] = jpeg_quality
                save_kwargs["optimize"] = True
                # Progressive JPEG is friendlier for large art uploads
                save_kwargs["progressive"] = True
                fmt = "JPEG"
            elif fmt == "PNG":
                save_kwargs["optimize"] = True

            canvas.save(dest_path, format=fmt, **save_kwargs)
            return fitted.width, fitted.height
    except ImageConvertError:
        raise
    except Exception as e:
        logger.exception("Failed to fit image to canvas")
        raise ImageConvertError(f"Failed to prepare image for display: {e}") from e


def needs_aspect_padding(
    source_path: Union[str, Path],
    canvas_size: Tuple[int, int] = FRAME_TV_CANVAS_SIZE,
    tolerance: float = 0.01,
) -> bool:
    """Return True if the image aspect ratio differs from the canvas (within tolerance)."""
    try:
        from PIL import Image, ImageOps
    except ImportError:
        return True

    try:
        with Image.open(source_path) as img:
            img = ImageOps.exif_transpose(img) or img
            w, h = img.size
    except Exception:
        return True

    if w <= 0 or h <= 0:
        return True
    image_ratio = w / h
    canvas_ratio = canvas_size[0] / canvas_size[1]
    return abs(image_ratio - canvas_ratio) > tolerance
