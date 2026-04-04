from __future__ import annotations

from pathlib import Path

from factory_analytics.database import Database
from factory_analytics.worker import WorkerLoop


def test_schedule_due_cameras_skips_when_pending_or_running_job_exists(tmp_path: Path):
    db = Database(path=tmp_path / "worker.db")
    camera = db.upsert_camera("camera_88_10")
    db.update_camera(camera["id"], {"enabled": True})
    db.schedule_job(camera["id"], payload={"source": "scheduler"})

    worker = WorkerLoop(db)
    worker._schedule_due_cameras()

    jobs = db.list_jobs(limit=20, camera_id=camera["id"])
    assert len(jobs) == 1


def test_schedule_due_groups(tmp_path: Path):
    db = Database(tmp_path / "test.db")
    worker = WorkerLoop(db)

    # Create group with short interval
    group = db.create_group("machine", "test_group", interval_seconds=1)
    camera = db.upsert_camera("test_cam", "Test Camera")
    db.update_camera(camera["id"], {"enabled": True})
    db.add_camera_to_group(camera["id"], group["id"])

    # Update last_run_at to be old
    db.update_group(group["id"], last_run_at="2020-01-01T00:00:00+00:00")

    # Schedule due groups
    worker._schedule_due_groups()

    # Should have scheduled a job
    assert db.has_active_group_jobs(group["id"])


def test_normalize_label_maps_working_variants():
    """normalize_label maps working-related labels to 'working'."""
    from factory_analytics.integrations.ollama import normalize_label

    assert normalize_label("working") == "working"
    assert normalize_label("Working") == "working"
    assert normalize_label("  working  ") == "working"


def test_normalize_label_maps_not_working_variants():
    """normalize_label maps not_working/idle-related labels to 'not_working'."""
    from factory_analytics.integrations.ollama import normalize_label

    assert normalize_label("not working") == "not_working"
    assert normalize_label("doing no work") == "not_working"
    assert normalize_label("idle") == "not_working"


def test_normalize_label_maps_no_person_variants():
    """normalize_label maps no_person variants to 'no_person'."""
    from factory_analytics.integrations.ollama import normalize_label

    assert normalize_label("no_person") == "no_person"
    assert normalize_label("no person") == "no_person"
    assert normalize_label("operator_missing") == "no_person"
    assert normalize_label("missing operator") == "no_person"
    assert normalize_label("no operator") == "no_person"
    assert normalize_label("worker missing") == "no_person"
    assert normalize_label("missing worker") == "no_person"
    assert normalize_label("no worker") == "no_person"
    assert normalize_label("no people") == "no_person"
    assert normalize_label("no human") == "no_person"


def test_normalize_label_maps_uncertain_variants():
    """normalize_label maps uncertain variants to 'uncertain'."""
    from factory_analytics.integrations.ollama import normalize_label

    assert normalize_label("uncertain") == "uncertain"
    assert normalize_label("unknown") == "uncertain"
    assert normalize_label("no extended analysis available") == "uncertain"
    assert normalize_label("no analysis available") == "uncertain"


def test_parse_classification_content_accepts_json_without_boxes():
    """_parse_classification_content accepts JSON without boxes field."""
    from factory_analytics.integrations.ollama import OpenAIClient

    client = OpenAIClient({"llm_url": "http://127.0.0.1:11434"})
    # JSON response without a boxes key
    content = '{"label": "working", "confidence": 0.9, "notes": "operator at station"}'
    result = client._parse_classification_content(content, group_mode=False)
    assert result["label"] == "working"
    assert result["confidence"] == 0.9
    assert result["notes"] == "operator at station"
    assert "boxes" not in result


def test_parse_classification_content_returns_only_label_confidence_notes():
    """_parse_classification_content returns only label/confidence/notes."""
    from factory_analytics.integrations.ollama import OpenAIClient

    client = OpenAIClient({"llm_url": "http://127.0.0.1:11434"})
    content = '{"label": "not_working", "confidence": 0.7, "notes": "idle", "boxes": [{"label": "person", "box": [0.1, 0.2, 0.3, 0.4]}]}'
    result = client._parse_classification_content(content, group_mode=False)
    assert result["label"] == "not_working"
    assert result["confidence"] == 0.7
    assert result["notes"] == "idle"
    assert "boxes" not in result
    assert set(result.keys()) == {"label", "confidence", "notes"}


def test_parse_classification_content_preserves_optional_observations():
    from factory_analytics.integrations.ollama import OpenAIClient

    client = OpenAIClient({"llm_url": "http://127.0.0.1:11434"})
    payload = client._parse_classification_content(
        '{"label":"not_working","confidence":0.62,"notes":"person visible but inactive","observations":[{"frame_index":0,"label":"not_working"},{"frame_index":1,"label":"working"}] }',
        group_mode=True,
    )

    assert payload["label"] == "not_working"
    assert payload["observations"] == [
        {"frame_index": 0, "label": "not_working", "notes": ""},
        {"frame_index": 1, "label": "working", "notes": ""},
    ]


def test_classify_images_replaces_seconds_placeholder_for_single_frame(monkeypatch):
    from factory_analytics.integrations.ollama import OpenAIClient

    client = OpenAIClient({"llm_url": "http://127.0.0.1:11434"})
    captured = {}

    def fake_send(prompt, image_paths):
        captured["prompt"] = prompt
        return '{"label":"working","confidence":0.9,"notes":"operator visible"}', {"choices": []}

    monkeypatch.setattr(client, "_send_request", fake_send)

    result = client.classify_images([Path("frame_0.jpg")], seconds_apart=3)

    assert result["label"] == "working"
    assert "{seconds}" not in captured["prompt"]
    assert "3" in captured["prompt"]


def test_update_daily_rollup_maps_new_label_set(tmp_path: Path):
    db = Database(path=tmp_path / "rollups.db")
    camera = db.upsert_camera("rollup_cam", "Rollup Cam")

    db.update_daily_rollup("2026-04-05", camera["id"], "not_working", 120)
    db.update_daily_rollup("2026-04-05", camera["id"], "no_person", 45)
    db.update_daily_rollup("2026-04-05", camera["id"], "working", 30)

    with db.connect() as conn:
        row = conn.execute(
            "SELECT working_seconds, idle_seconds, stopped_seconds, uncertain_seconds FROM daily_rollups WHERE day=? AND camera_id=?",
            ("2026-04-05", camera["id"]),
        ).fetchone()

    assert row["working_seconds"] == 30
    assert row["idle_seconds"] == 120
    assert row["stopped_seconds"] == 45
    assert row["uncertain_seconds"] == 0


def test_services_module_no_longer_imports_image_annotations():
    source = Path("factory_analytics/services.py").read_text()
    assert "image_annotations" not in source
    assert "draw_person_boxes" not in source
