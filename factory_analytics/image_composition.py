from __future__ import annotations

from math import ceil, sqrt
from pathlib import Path


def _load_pil():
    try:
        from PIL import Image, ImageDraw
    except ImportError as exc:
        raise RuntimeError(
            "Pillow is required for image composition. Install dependencies with './.venv/bin/pip install -r requirements.txt'"
        ) from exc
    return Image, ImageDraw


def merge_group_snapshots(images: list[tuple[str, Path]], output_path: Path) -> Path:
    Image, ImageDraw = _load_pil()
    opened = [(name, Image.open(path).convert("RGB")) for name, path in images]
    if not opened:
        raise RuntimeError("No images to merge")
    tile_w = max(img.width for _, img in opened)
    tile_h = max(img.height for _, img in opened)
    cols = max(1, int(ceil(sqrt(len(opened)))))
    rows = int(ceil(len(opened) / cols))
    canvas = Image.new("RGB", (cols * tile_w, rows * tile_h), color="black")
    draw = ImageDraw.Draw(canvas)
    for idx, (name, img) in enumerate(opened):
        x = (idx % cols) * tile_w
        y = (idx // cols) * tile_h
        canvas.paste(img, (x, y))
        draw.rectangle([x, y, x + 240, y + 28], fill=(0, 0, 0))
        draw.text((x + 8, y + 6), name, fill=(255, 255, 255))
    output_path.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(output_path, format="JPEG", quality=95)
    return output_path
