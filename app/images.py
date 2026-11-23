"""Validate uploaded bytes, then store only newly encoded JPEG images."""

from io import BytesIO
from pathlib import Path
import re
import uuid
import warnings

from flask import current_app
from PIL import Image, ImageOps, UnidentifiedImageError

FILENAME = re.compile(r"^[a-f0-9]{32}\.jpg$")
MAX_IMAGE_BYTES = 5 * 1024 * 1024
MAX_IMAGE_COUNT = 5
MAX_TOTAL_IMAGE_BYTES = 25 * 1024 * 1024


def image_path(filename):
    if not filename or not FILENAME.fullmatch(filename):
        raise ValueError("Invalid image reference.")
    root = Path(current_app.config["UPLOAD_FOLDER"]).resolve()
    path = root / filename
    if path.resolve().parent != root or path.is_symlink():
        raise ValueError("Invalid image location.")
    return path


def image_exists(filename):
    try:
        return image_path(filename).is_file()
    except (ValueError, OSError):
        return False


def discard_image(filename):
    if filename:
        try:
            image_path(filename).unlink(missing_ok=True)
        except (OSError, ValueError):
            # Reconciliation reports failed post-commit cleanup; do not destroy
            # a successful database transaction because an old file is locked.
            current_app.logger.warning("image_cleanup_deferred")


def _normalized_image(upload, *, max_dimension=1600, quality=85):
    """Return a safe JPEG copy without storing the original upload.

    Opening, verifying, reopening and re-encoding the image makes the bytes
    suitable for both permanent listings and the optional vision provider.
    """
    if not upload or not upload.filename:
        raise ValueError("Choose one product photo.")
    content = upload.stream.read(MAX_IMAGE_BYTES + 1)
    if not content or len(content) > MAX_IMAGE_BYTES:
        raise ValueError("Photo must be nonempty and no larger than 5 MiB.")
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(BytesIO(content)) as source:
                if source.format not in ("JPEG", "PNG") or getattr(source, "n_frames", 1) != 1:
                    raise ValueError("Use a single JPEG or PNG image.")
                if source.width * source.height > 12000000:
                    raise ValueError("Photo must contain no more than 12 million pixels.")
                source.verify()
            with Image.open(BytesIO(content)) as source:
                normalized = ImageOps.exif_transpose(source).convert("RGBA")
                normalized.thumbnail((max_dimension, max_dimension))
                # A fresh RGB image intentionally carries no original EXIF or other metadata.
                clean = Image.new("RGB", normalized.size, "white")
                clean.paste(normalized, mask=normalized.getchannel("A"))
                encoded = BytesIO()
                clean.save(encoded, format="JPEG", quality=quality)
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError, Image.DecompressionBombWarning):
        raise ValueError("That file is not a supported, readable photo.") from None
    return encoded.getvalue(), len(content)


def normalized_image_bytes(upload, *, max_dimension=1600, quality=85):
    """Compatibility API used by permanent images and optional AI analysis."""
    return _normalized_image(upload, max_dimension=max_dimension, quality=quality)[0]


def _store_clean_bytes(clean_bytes):
    name = uuid.uuid4().hex + ".jpg"
    destination = image_path(name)
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_suffix(".pending")
    try:
        with temporary.open("xb") as stream:
            stream.write(clean_bytes)
        temporary.replace(destination)
    except OSError:
        temporary.unlink(missing_ok=True)
        raise
    return name


def store_image(upload):
    if not upload or not upload.filename:
        return None
    clean_bytes = normalized_image_bytes(upload, max_dimension=1600, quality=85)
    return _store_clean_bytes(clean_bytes)


def selected_uploads(uploads):
    """Remove only the empty placeholder produced by an optional file input."""
    if uploads is None:
        return []
    if not isinstance(uploads, (list, tuple)):
        uploads = [uploads]
    return [upload for upload in uploads if upload and upload.filename]


def discard_images(filenames):
    for filename in dict.fromkeys(filename for filename in filenames if filename):
        discard_image(filename)


def store_images(uploads):
    """Normalize/store an ordered group, compensating every partial file write."""
    uploads = selected_uploads(uploads)
    if len(uploads) > MAX_IMAGE_COUNT:
        raise ValueError("Choose no more than five product photos.")
    stored = []
    total = 0
    try:
        for upload in uploads:
            clean, raw_size = _normalized_image(upload, max_dimension=1600, quality=85)
            total += raw_size
            if total > MAX_TOTAL_IMAGE_BYTES:
                raise ValueError("Product photos must total no more than 25 MiB.")
            stored.append(_store_clean_bytes(clean))
    except (ValueError, OSError):
        discard_images(stored)
        raise
    return stored


def gallery_references(product):
    """Return all database references in order, with legacy cover fallback."""
    names = [row.filename for row in getattr(product, "gallery_images", ())]
    if not names and product.image_filename:
        names = [product.image_filename]
    return list(dict.fromkeys(names))


def usable_gallery(product):
    """Return existing safe files without mutating broken database references."""
    return [name for name in gallery_references(product) if image_exists(name)]
