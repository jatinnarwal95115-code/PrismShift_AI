from io import BytesIO
from pathlib import Path
from uuid import uuid4

from PIL import Image, ImageOps, UnidentifiedImageError
from fastapi import UploadFile, HTTPException

from Backend.services.database import UPLOAD_DIR

ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB

# Phone photos are often 4000+ px. The model downsizes them anyway, so shrinking
# first makes generation much faster without hurting the result.
MAX_DIMENSION = 1600


def _prepare_image(content: bytes, extension: str) -> bytes:
    """Validate the image, apply its EXIF rotation, shrink it, re-encode it."""

    with Image.open(BytesIO(content)) as image:
        image.load()
        image = ImageOps.exif_transpose(image)

        if max(image.size) > MAX_DIMENSION:
            image.thumbnail((MAX_DIMENSION, MAX_DIMENSION))

        output = BytesIO()

        if extension in {".jpg", ".jpeg"}:
            image.convert("RGB").save(output, "JPEG", quality=90)
        elif extension == ".png":
            image.save(output, "PNG")
        else:
            image.save(output, "WEBP", quality=90)

        return output.getvalue()


async def save_uploaded_image(file: UploadFile) -> str:
    """Validate and save an uploaded image. Returns its saved path."""

    if not file.filename:
        raise HTTPException(status_code=400, detail="No image selected.")

    extension = Path(file.filename).suffix.lower()

    if extension not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail="Only JPG, JPEG, PNG, and WEBP images are allowed."
        )

    content = await file.read()

    if not content:
        raise HTTPException(status_code=400, detail="The uploaded file is empty.")

    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=413,
            detail="Image size must not exceed 10 MB."
        )

    try:
        content = _prepare_image(content, extension)

    except (UnidentifiedImageError, OSError, ValueError, Image.DecompressionBombError):
        raise HTTPException(
            status_code=400,
            detail="The uploaded file is not a valid image."
        )

    filename = f"{uuid4().hex}{extension}"
    destination = UPLOAD_DIR / filename

    destination.write_bytes(content)

    return str(destination)


def get_image_path(filename: str) -> Path:
    """Safely find an image inside the upload directory."""

    path = (UPLOAD_DIR / filename).resolve()

    if path.parent != UPLOAD_DIR.resolve():
        raise ValueError("Invalid image filename.")

    if not path.exists():
        raise FileNotFoundError("Uploaded image not found.")

    return path