from __future__ import annotations

import hashlib
from io import BytesIO

from PIL import Image, UnidentifiedImageError


class ImageValidationError(ValueError):
    pass


def render_safe_avatar_png(image_bytes: bytes, *, max_size: int = 256) -> tuple[bytes, int, int, str]:
    try:
        with Image.open(BytesIO(image_bytes)) as image:
            image.load()
            image.thumbnail((max_size, max_size))
            safe_image = image.convert("RGBA")
    except (OSError, SyntaxError, UnidentifiedImageError) as exc:
        raise ImageValidationError("Avatar must be a valid image.") from exc

    output = BytesIO()
    safe_image.save(output, format="PNG")
    png_bytes = output.getvalue()
    sha256 = hashlib.sha256(png_bytes).hexdigest()
    return png_bytes, safe_image.width, safe_image.height, sha256
