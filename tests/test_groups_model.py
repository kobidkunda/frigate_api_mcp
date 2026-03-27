from pathlib import Path

from factory_analytics.database import Database


def test_camera_can_belong_to_multiple_groups(tmp_path: Path):
    db = Database(tmp_path / "test.db")
    cam = db.upsert_camera("camera_1")
    machine = db.create_group("machine", "machine 1")
    room = db.create_group("room", "room 1 factory")

    db.add_camera_to_group(cam["id"], machine["id"])
    db.add_camera_to_group(cam["id"], room["id"])

    groups = db.list_camera_groups(cam["id"])
    assert len(groups) == 2
    assert {g["group_type"] for g in groups} == {"machine", "room"}
