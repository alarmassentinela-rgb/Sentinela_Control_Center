import io
import os
import uuid

from fastapi import APIRouter, HTTPException, UploadFile, File
from PIL import Image, ImageOps

from app.core.deps import CurrentUser
from app.core.config import settings

router = APIRouter()

MAX_BYTES = 10 * 1024 * 1024      # 10 MB de subida
MAX_EDGE = 1600                    # lado mayor de la imagen final
THUMB_EDGE = 400                   # lado mayor del thumbnail
SUBDIR = "posts"                   # /app/media/posts


@router.post("/image")
async def upload_image(current_user: CurrentUser, file: UploadFile = File(...)):
    """Sube una imagen (JPEG/PNG/…); la reorienta, comprime y genera thumbnail.

    Devuelve {url, thumbnail_url} apuntando a MEDIA_URL. Requiere sesión.
    """
    data = await file.read()
    if not data:
        raise HTTPException(400, "Archivo vacío")
    if len(data) > MAX_BYTES:
        raise HTTPException(400, "La imagen supera el máximo de 10 MB")

    try:
        img = Image.open(io.BytesIO(data))
        img = ImageOps.exif_transpose(img)   # respeta la orientación del celular
        img = img.convert("RGB")             # descarta alfa/EXIF, normaliza a RGB
    except Exception:
        raise HTTPException(400, "El archivo no es una imagen válida")

    dest_dir = os.path.join(settings.MEDIA_ROOT, SUBDIR)
    os.makedirs(dest_dir, exist_ok=True)
    name = uuid.uuid4().hex
    full_name = f"{name}.jpg"
    thumb_name = f"{name}_t.jpg"

    # Imagen principal (lado mayor <= MAX_EDGE)
    main = img.copy()
    main.thumbnail((MAX_EDGE, MAX_EDGE), Image.LANCZOS)
    main.save(os.path.join(dest_dir, full_name), "JPEG", quality=85, optimize=True)

    # Thumbnail
    thumb = img.copy()
    thumb.thumbnail((THUMB_EDGE, THUMB_EDGE), Image.LANCZOS)
    thumb.save(os.path.join(dest_dir, thumb_name), "JPEG", quality=80, optimize=True)

    base = settings.MEDIA_URL.rstrip("/")
    return {
        "url": f"{base}/{SUBDIR}/{full_name}",
        "thumbnail_url": f"{base}/{SUBDIR}/{thumb_name}",
    }
