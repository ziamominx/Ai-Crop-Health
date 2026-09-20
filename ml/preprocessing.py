"""Image preprocessing for the crop-disease model (shared by real and demo paths)."""
import base64
import io

import numpy as np

TARGET_SIZE = (224, 224)


def preprocess_image(image_bytes: bytes) -> "np.ndarray":
    """Decode an image and prepare a normalised (1, 224, 224, 3) float tensor.

    Uses Pillow so heavy framework imports (TF/torch) stay optional. When a real
    TF model is plugged in, swap in the same resize/normalisation the model was
    trained with (e.g. keras.applications preprocess_input).
    """
    from PIL import Image

    img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    img = img.resize(TARGET_SIZE)
    arr = np.asarray(img, dtype=np.float32) / 255.0
    return np.expand_dims(arr, axis=0)


def make_demo_thumbnail(image_bytes: bytes, max_w: int = 320) -> str | None:
    """Small JPEG data-URL thumbnail for UI lists (best-effort)."""
    try:
        from PIL import Image

        img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        scale = min(1.0, max_w / img.width)
        thumb = img.resize((max(1, int(img.width * scale)), max(1, int(img.height * scale))))
        buf = io.BytesIO()
        thumb.save(buf, format="JPEG", quality=72)
        return "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode()
    except Exception:
        return None
