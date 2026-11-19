"""File uploads.

* Listing photos are public (Cloudinary 'upload' type, or ./uploads/public).
* KYC documents are private (Cloudinary 'authenticated' type, or
  ./uploads/private which is never served directly). Admins get a short-lived
  signed link.
"""
import os
import time
import uuid
from pathlib import Path

from fastapi import UploadFile

from app.core.config import get_settings
from app.core.errors import AppError

settings = get_settings()

ALLOWED_IMAGE = {"image/jpeg": "jpg", "image/png": "png", "image/webp": "webp"}
ALLOWED_DOC = {**ALLOWED_IMAGE, "application/pdf": "pdf"}
MAX_BYTES = 5 * 1024 * 1024

if settings.use_cloudinary:
    import cloudinary
    import cloudinary.uploader
    import cloudinary.utils

    cloudinary.config(
        cloud_name=settings.cloudinary_cloud_name,
        api_key=settings.cloudinary_api_key,
        api_secret=settings.cloudinary_api_secret,
        secure=True,
    )


async def _read_checked(file: UploadFile, allowed: dict[str, str]) -> tuple[bytes, str]:
    if file.content_type not in allowed:
        raise AppError("bad_file", 415)
    data = await file.read(MAX_BYTES + 1)
    if len(data) > MAX_BYTES or not data:
        raise AppError("bad_file", 413)
    return data, allowed[file.content_type]


async def save_public_image(file: UploadFile) -> str:
    data, ext = await _read_checked(file, ALLOWED_IMAGE)
    if settings.use_cloudinary:
        result = cloudinary.uploader.upload(
            data, folder="dhs/listings", resource_type="image",
            transformation=[{"width": 1600, "crop": "limit", "quality": "auto", "fetch_format": "auto"}],
        )
        return result["secure_url"]
    folder = Path(settings.local_upload_dir) / "public"
    folder.mkdir(parents=True, exist_ok=True)
    name = f"{uuid.uuid4().hex}.{ext}"
    (folder / name).write_bytes(data)
    return f"{settings.public_base_url}/media/{name}"


async def save_private_document(file: UploadFile) -> tuple[str, str]:
    """Returns (storage_key, content_type)."""
    data, ext = await _read_checked(file, ALLOWED_DOC)
    if settings.use_cloudinary:
        result = cloudinary.uploader.upload(
            data, folder="dhs/kyc", type="authenticated",
            resource_type="raw" if ext == "pdf" else "image",
        )
        return f"cld:{result['resource_type']}:{result['public_id']}", file.content_type
    folder = Path(settings.local_upload_dir) / "private"
    folder.mkdir(parents=True, exist_ok=True)
    name = f"{uuid.uuid4().hex}.{ext}"
    (folder / name).write_bytes(data)
    return f"local:{name}", file.content_type


def private_document_url(storage_key: str, doc_id: int) -> str:
    """A link that works for ~5 minutes (Cloudinary) or an admin-only API path (local)."""
    if storage_key.startswith("cld:"):
        _, resource_type, public_id = storage_key.split(":", 2)
        url, _ = cloudinary.utils.cloudinary_url(
            public_id, resource_type=resource_type, type="authenticated", sign_url=True,
            expires_at=int(time.time()) + 300, secure=True,
        )
        return url
    return f"/admin/kyc/documents/{doc_id}/file"


def local_private_path(storage_key: str) -> Path | None:
    if not storage_key.startswith("local:"):
        return None
    name = os.path.basename(storage_key.split(":", 1)[1])
    return Path(settings.local_upload_dir) / "private" / name


def delete_private_document(storage_key: str) -> None:
    if storage_key.startswith("cld:") and settings.use_cloudinary:
        _, resource_type, public_id = storage_key.split(":", 2)
        cloudinary.uploader.destroy(public_id, resource_type=resource_type, type="authenticated")
        return
    path = local_private_path(storage_key)
    if path and path.exists():
        path.unlink()
