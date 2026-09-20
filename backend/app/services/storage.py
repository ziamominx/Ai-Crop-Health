"""Object-storage abstraction: LOCAL (demo fallback) / SUPABASE / CLOUDINARY.

Stores only URLs/paths in PostgreSQL; binaries go to the configured provider.
"""
import os
import secrets
import tempfile
import uuid

from fastapi import HTTPException, UploadFile

from app.config import settings

ALLOWED_CONTENT_TYPES = {"image/jpeg", "image/png", "image/webp"}
ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}

_uploads_dir_cache: str | None = None


def uploads_dir() -> str:
    """Writable directory for locally-stored images (resolved once per process).

    Prefers <CWD>/uploads (local dev). On read-only working directories —
    serverless platforms like Vercel — falls back to a temp directory, which
    keeps image storage functional (albeit ephemeral) instead of crashing.
    """
    global _uploads_dir_cache
    if _uploads_dir_cache is not None:
        return _uploads_dir_cache

    candidates = [
        os.path.join(os.getcwd(), settings.UPLOAD_DIR),
        os.path.join(tempfile.gettempdir(), "agricure", "uploads"),
    ]
    for candidate in candidates:
        try:
            os.makedirs(candidate, exist_ok=True)
            probe = os.path.join(candidate, ".write_probe")
            with open(probe, "w") as fh:
                fh.write("x")
            os.unlink(probe)
            _uploads_dir_cache = candidate
            if candidate != candidates[0]:
                print(f"[Agricure] CWD is read-only — storing images in {candidate} "
                      "(ephemeral on serverless; use SUPABASE/CLOUDINARY to persist).")
            return candidate
        except (OSError, PermissionError):
            continue
    raise HTTPException(status_code=507,
                        detail="No writable directory available for image storage.")


def validate_image(file: UploadFile) -> None:
    """File-type + size validation before anything touches storage."""
    ext = os.path.splitext(file.filename or "")[1].lower()
    if file.content_type not in ALLOWED_CONTENT_TYPES and ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=415, detail="Only JPEG, PNG or WebP images are allowed.")


async def save_image(file: UploadFile, farmer_id: int) -> tuple[str, str]:
    """Persist an uploaded image. Returns (public_url, storage_path).

    storage_path is the provider-local reference (local file path for LOCAL mode).
    """
    validate_image(file)
    data = await file.read()
    max_bytes = settings.MAX_UPLOAD_MB * 1024 * 1024
    if len(data) == 0:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")
    if len(data) > max_bytes:
        raise HTTPException(status_code=413,
                            detail=f"Image too large (max {settings.MAX_UPLOAD_MB} MB).")

    ext = (os.path.splitext(file.filename or "")[1].lower() or ".jpg")
    name = f"f{farmer_id}_{uuid.uuid4().hex[:12]}{ext}"

    provider = settings.STORAGE_PROVIDER.upper()
    if provider == "SUPABASE":
        return _save_supabase(data, name)
    if provider == "CLOUDINARY":
        return _save_cloudinary(data, name)
    return _save_local(data, name)


def _save_local(data: bytes, name: str) -> tuple[str, str]:
    directory = uploads_dir()
    path = os.path.join(directory, name)
    with open(path, "wb") as fh:
        fh.write(data)
    # Relative URL: the browser resolves it against the current origin. This
    # works unchanged locally (Vite proxies /api) and on Vercel (same-domain
    # /api rewrite) — no PUBLIC_BASE_URL misconfiguration can break images.
    url = f"/api/images/{name}"
    return url, path


def _save_supabase(data: bytes, name: str) -> tuple[str, str]:
    if not settings.SUPABASE_URL or not settings.SUPABASE_SERVICE_KEY:
        # Graceful demo fallback instead of a hard failure
        print("[Agricure] SUPABASE storage not configured — falling back to LOCAL storage.")
        return _save_local(data, name)
    import httpx

    url = f"{settings.SUPABASE_URL}/storage/v1/object/{settings.SUPABASE_BUCKET}/{name}"
    headers = {
        "Authorization": f"Bearer {settings.SUPABASE_SERVICE_KEY}",
        "Content-Type": "application/octet-stream",
    }
    resp = httpx.post(url, content=data, headers=headers, timeout=30)
    if resp.status_code >= 300:
        raise HTTPException(status_code=502, detail=f"Supabase upload failed: {resp.text[:200]}")
    public = f"{settings.SUPABASE_URL}/storage/v1/object/public/{settings.SUPABASE_BUCKET}/{name}"
    return public, name


def _save_cloudinary(data: bytes, name: str) -> tuple[str, str]:
    if not (settings.CLOUDINARY_CLOUD_NAME and settings.CLOUDINARY_API_KEY
            and settings.CLOUDINARY_API_SECRET):
        print("[Agricure] CLOUDINARY not configured — falling back to LOCAL storage.")
        return _save_local(data, name)
    import time
    import hashlib
    import httpx

    timestamp = int(time.time())
    folder = "agricure"
    public_id = f"{folder}/{os.path.splitext(name)[0]}"
    signature = hashlib.sha1(
        f"public_id={public_id}&timestamp={timestamp}{settings.CLOUDINARY_API_SECRET}"
    ).hexdigest()
    resp = httpx.post(
        f"https://api.cloudinary.com/v1_1/{settings.CLOUDINARY_CLOUD_NAME}/image/upload",
        data={"public_id": public_id, "timestamp": timestamp, "api_key": settings.CLOUDINARY_API_KEY,
              "signature": signature},
        files={"file": ("image", data)},
        timeout=30,
    )
    if resp.status_code >= 300:
        raise HTTPException(status_code=502, detail=f"Cloudinary upload failed: {resp.text[:200]}")
    return resp.json()["secure_url"], public_id


def resolve_url(image_url: str | None, image_path: str | None) -> str | None:
    """Best URL for the frontend to display (relative, same-origin safe)."""
    if image_url:
        return image_url
    if image_path and os.path.exists(image_path):
        return f"/api/images/{os.path.basename(image_path)}"
    return None
