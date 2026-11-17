import os
from PIL import Image, ImageOps

ALLOWED = {".jpeg", ".jpg", ".png", ".webp"}
MAX_BYTES = 5 * 1024 * 1024
MAX_WIDTH = 1600
MAX_PHOTOS = 10


def validate_photo(path):
    """Return an error message, or None if the photo is fine."""
    name = os.path.basename(path)

    if not os.path.exists(path):
        return f"{name}: not found"

    if os.path.splitext(path)[1].lower() not in ALLOWED:
        return f"{name}: unsupported type"

    if os.path.getsize(path) > MAX_BYTES:
        return f"{name}: too large"

    try:
        with Image.open(path) as img:
            img.verify()
    except Exception:
        return f"{name}: not a valid image"

    return None


def to_rgb(img):
    """Convert to RGB; put see-through areas on a white background."""
    has_alpha = img.mode in ("RGBA", "LA") or "transparency" in img.info
    if has_alpha:
        img = img.convert("RGBA")
        canvas = Image.new("RGB", img.size, "white")
        canvas.paste(img, mask=img.split()[-1])
        return canvas
    return img.convert("RGB")


def process_photos(photo_paths, slug, out_root="previews"):
    """Return (saved, problems)."""
    if not photo_paths:
        return [], ["no photos provided"]

    images = []
    problems = []
    saved = []

    for path in photo_paths:
        error = validate_photo(path)
        if error:
            problems.append(error)
            continue
        with Image.open(path) as img:
            img = ImageOps.exif_transpose(img)
            img = to_rgb(img)
            img.thumbnail((MAX_WIDTH, 10000))
            images.append(img)

    for i, img in enumerate(images):
        if img.width > img.height:
            images.insert(0, images.pop(i))
            break

    if len(images) > MAX_PHOTOS:
        problems.append(f"only first {MAX_PHOTOS} photos used, {len(images) - MAX_PHOTOS}")
        images = images[:MAX_PHOTOS]

    if images:
        folder = os.path.join(out_root, slug, "assets")
        os.makedirs(folder, exist_ok=True)
        for n, img in enumerate(images, start=1):
            out_path = os.path.join(folder, f"photo-{n}.jpg")
            img.save(out_path, "JPEG", quality=85)
            saved.append(out_path)

    return saved, problems
