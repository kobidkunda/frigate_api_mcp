"""
ImagePipeline: Frame sampling, resizing, compression, and collage building
for LLM vision model input optimization.
"""

from __future__ import annotations

import io
import time
from pathlib import Path
from typing import Any

logger: Any = None


def _get_logger():
    global logger
    if logger is None:
        from factory_analytics.logging_setup import setup_logging

        logger = setup_logging()
    return logger


def _load_pil():
    try:
        from PIL import Image, ImageDraw, ImageFont
    except ImportError as exc:
        raise RuntimeError(
            "Pillow is required for image pipeline. Install with: pip install Pillow"
        ) from exc
    return Image, ImageDraw, ImageFont


def fetch_frames(
    frigate_client,
    camera_name: str,
    count: int,
    interval_sec: int = 1,
) -> list:
    Image, _, _ = _load_pil()
    frames = []
    for i in range(count):
        raw = frigate_client.fetch_latest_snapshot_to_bytes(camera_name)
        img = Image.open(io.BytesIO(raw)).convert("RGB")
        frames.append(img)
        if i < count - 1:
            time.sleep(interval_sec)
    return frames


def resize_pil_image(pil_image, max_dimension: int):
    Image, _, _ = _load_pil()
    if max_dimension <= 0:
        return pil_image.convert("RGB")

    w, h = pil_image.size
    if max(w, h) <= max_dimension:
        return pil_image.convert("RGB")

    scale = max_dimension / max(w, h)
    new_w = int(w * scale)
    new_h = int(h * scale)
    return pil_image.resize((new_w, new_h), Image.LANCZOS).convert("RGB")


def compress_pil_image_to_file(pil_image, output_path: Path, quality: int) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    pil_image.save(str(output_path), "JPEG", quality=quality)
    return output_path


def build_vertical_strip(frames: list, camera_name: str, output_path: Path) -> Path:
    Image, ImageDraw, ImageFont = _load_pil()

    if not frames:
        raise RuntimeError("No frames to build strip")
    if len(frames) == 1:
        img = frames[0]
        output_path.parent.mkdir(parents=True, exist_ok=True)
        img.save(str(output_path), "JPEG", quality=95)
        return output_path

    w = max(f.width for f in frames)
    h_total = sum(f.height for f in frames)
    label_h = 30

    canvas = Image.new("RGB", (w, h_total + label_h), "black")
    draw = ImageDraw.Draw(canvas)

    try:
        font = ImageFont.load_default()
    except Exception:
        font = None

    draw.rectangle([0, 0, w - 1, label_h - 1], fill=(30, 30, 30))
    draw.text(
        (8, 8),
        f"{camera_name} ({len(frames)} frames)",
        fill=(200, 200, 200),
        font=font,
    )

    y = label_h
    for f in frames:
        canvas.paste(f, (0, y))
        y += f.height

    output_path.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(str(output_path), "JPEG", quality=95)
    return output_path


def build_group_collage(
    camera_strips: list[tuple[str, Path]],
    output_path: Path,
) -> Path:
    import shutil

    Image, ImageDraw, ImageFont = _load_pil()

    if not camera_strips:
        raise RuntimeError("No strips to collage")
    if len(camera_strips) == 1:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(str(camera_strips[0][1]), str(output_path))
        return output_path

    strips = [(name, Image.open(path).convert("RGB")) for name, path in camera_strips]

    total_w = sum(img.width for _, img in strips)
    max_h = max(img.height for _, img in strips)
    label_h = 30
    canvas_h = max_h + label_h

    canvas = Image.new("RGB", (total_w, canvas_h), "black")
    draw = ImageDraw.Draw(canvas)

    try:
        font = ImageFont.load_default()
    except Exception:
        font = None

    x = 0
    for name, img in strips:
        draw.rectangle([x, 0, x + img.width - 1, label_h - 1], fill=(30, 30, 30))
        draw.text((x + 8, 8), name, fill=(200, 200, 200), font=font)
        canvas.paste(img, (x, label_h))
        x += img.width

    output_path.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(str(output_path), "JPEG", quality=95)
    return output_path
