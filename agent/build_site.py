import json
import os
import shutil
import stat
from pathlib import Path

from agent.config import TEMPLATE_DIR, OUTPUT_DIR

CARDS = 6  # gallery cards in the template


def _force_delete(func, path, _exc):
    """Windows: make read-only files writable, then delete them."""
    os.chmod(path, stat.S_IWRITE)
    func(path)


def _photo_paths(photos):
    paths = []
    for p in photos or []:
        if isinstance(p, dict):
            p = p.get("path") or p.get("file") or p.get("output")
        if p:
            paths.append(Path(p))
    return paths


def build_site(state):
    slug = state["business"]["slug"]
    template = Path(state.get("template_dir") or TEMPLATE_DIR)
    out = OUTPUT_DIR / slug
    if out.exists():
        shutil.rmtree(out, onexc=_force_delete)
    shutil.copytree(template, out, ignore=shutil.ignore_patterns(".git", "__pycache__"))

    # 1. Text: the pages load data/site-data.js, so write that file ourselves
    data_dir = out / "data"
    data_dir.mkdir(exist_ok=True)
    body = json.dumps(state["site_data"], ensure_ascii=False, indent=2)
    (data_dir / "site-data.js").write_text(
        "window.SITE_DATA = " + body + ";\n", encoding="utf-8"
    )
    old_copy = out / "site-data.js"  # old template file, if it exists
    if old_copy.exists():
        old_copy.unlink()

    # 2. Photos: remove template sample photos, copy the business photos
    img_dir = out / "images"
    img_dir.mkdir(exist_ok=True)
    for f in img_dir.glob("photo-*"):
        f.unlink()

    photos = _photo_paths(state.get("photos"))
    for i in range(1, CARDS + 1):
        if not photos:
            break
        src = photos[(i - 1) % len(photos)]
        shutil.copy(src, img_dir / f"photo-{i}{src.suffix.lower()}")

    return {"site_path": str(out), "photo_count": len(photos)}