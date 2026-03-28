from pathlib import Path

from PIL import Image

from factory_analytics.image_composition import merge_group_snapshots


def test_merge_group_snapshots_creates_full_resolution_composite(tmp_path: Path):
    a = tmp_path / "a.jpg"
    b = tmp_path / "b.jpg"
    out = tmp_path / "out.jpg"
    Image.new("RGB", (400, 300), color="red").save(a)
    Image.new("RGB", (400, 300), color="blue").save(b)

    merge_group_snapshots([("camera_a", a), ("camera_b", b)], out)

    assert out.exists()
    merged = Image.open(out)
    assert merged.width >= 400
    assert merged.height >= 300


def test_merge_group_snapshots_preserves_original_dimensions_in_grid(tmp_path: Path):
    a = tmp_path / "a.jpg"
    b = tmp_path / "b.jpg"
    c = tmp_path / "c.jpg"
    out = tmp_path / "grid.jpg"
    Image.new("RGB", (1920, 1080), color="red").save(a)
    Image.new("RGB", (1280, 720), color="blue").save(b)
    Image.new("RGB", (800, 600), color="green").save(c)

    merge_group_snapshots([("camera_a", a), ("camera_b", b), ("camera_c", c)], out)

    merged = Image.open(out)
    assert merged.width >= 1920 + 1280
    assert merged.height >= 1080 + 600
