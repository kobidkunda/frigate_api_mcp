from __future__ import annotations

from pathlib import Path


def _load_pil():
    try:
        from PIL import Image, ImageDraw
    except ImportError as exc:
        raise RuntimeError(
            "Pillow is required for image annotation. Install dependencies with './.venv/bin/pip install -r requirements.txt'"
        ) from exc
    return Image, ImageDraw


def draw_person_boxes(
    input_image: Path, output_image: Path, boxes: list[dict], quality: int = 80
) -> Path:
    Image, ImageDraw = _load_pil()
    image = Image.open(input_image).convert("RGB")
    draw = ImageDraw.Draw(image)
    width, height = image.size

    for item in boxes:
        box = item.get("box") or []
        if len(box) != 4:
            continue
        x, y, w, h = box
        left = max(0, min(width, int(x * width)))
        top = max(0, min(height, int(y * height)))
        right = max(left, min(width, int((x + w) * width)))
        bottom = max(top, min(height, int((y + h) * height)))
        draw.rectangle([left, top, right, bottom], outline=(255, 0, 0), width=4)

    output_image.parent.mkdir(parents=True, exist_ok=True)
    image.save(output_image, format="JPEG", quality=quality)
    return output_image
