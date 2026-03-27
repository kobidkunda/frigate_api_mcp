from pathlib import Path

from PIL import Image

from factory_analytics.image_annotations import draw_person_boxes


def test_draw_person_boxes_writes_annotated_image(tmp_path: Path):
    input_image = tmp_path / "in.jpg"
    output_image = tmp_path / "out.jpg"
    Image.new("RGB", (400, 300), color="white").save(input_image)

    boxes = [{"label": "person", "box": [0.1, 0.2, 0.3, 0.4]}]
    draw_person_boxes(input_image, output_image, boxes)

    assert output_image.exists()
    assert output_image.stat().st_size > 0
