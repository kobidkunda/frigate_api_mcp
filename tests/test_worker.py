from __future__ import annotations

import json
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


def test_classify_images_replaces_seconds_placeholder_for_fractional_interval(monkeypatch):
    from factory_analytics.integrations.ollama import OpenAIClient

    client = OpenAIClient({"llm_url": "http://127.0.0.1:11434"})
    captured = {}

    def fake_send(prompt, image_paths):
        captured["prompt"] = prompt
        return '{"label":"working","confidence":0.9,"notes":"operator visible"}', {"choices": []}

    monkeypatch.setattr(client, "_send_request", fake_send)

    result = client.classify_images([Path("frame_0.jpg"), Path("frame_1.jpg")], seconds_apart=0.5)

    assert result["label"] == "working"
    assert "{seconds}" not in captured["prompt"]
    assert "0.5" in captured["prompt"]


def test_image_settings_expand_capture_count_by_window(tmp_path: Path):
    from factory_analytics.services import AnalyticsService

    db = Database(path=tmp_path / "image_settings.db")
    service = AnalyticsService(db)
    db.update_settings({"llm_frames_per_process": 1, "llm_seconds_window": 3})

    settings = service._get_image_settings()

    assert settings["frames"] == 3
    assert settings["seconds_window"] == 3
    assert settings["frame_interval_seconds"] == 1.0


def test_image_settings_compute_interval_for_multi_fps(tmp_path: Path):
    from factory_analytics.services import AnalyticsService

    db = Database(path=tmp_path / "image_settings_rate.db")
    service = AnalyticsService(db)
    db.update_settings({"llm_frames_per_process": 2, "llm_seconds_window": 3})

    settings = service._get_image_settings()

    assert settings["frames"] == 6
    assert settings["seconds_window"] == 3
    assert settings["frame_interval_seconds"] == 0.5


def test_process_single_job_passes_real_capture_interval_and_prompt_timing(tmp_path: Path, monkeypatch):
    from pathlib import Path as SysPath

    from factory_analytics.services import AnalyticsService

    db = Database(path=tmp_path / "single_job_interval.db")
    service = AnalyticsService(db)
    db.update_settings({"llm_frames_per_process": 2, "llm_seconds_window": 3})

    camera = db.upsert_camera("cam_interval", "Interval Cam")
    job = db.schedule_job(camera["id"], payload={"source": "test"})

    captured = {}

    class FakeFrame:
        def save(self, target, fmt, quality=100):
            SysPath(target).parent.mkdir(parents=True, exist_ok=True)
            SysPath(target).write_bytes(b"frame")

    def fake_fetch_frames(frigate, camera_name, count, interval_sec=1):
        captured["camera_name"] = camera_name
        captured["count"] = count
        captured["interval_sec"] = interval_sec
        return [FakeFrame() for _ in range(count)]

    def fake_resize(image, max_dim):
        return image

    class FakeSavedFrame:
        def __init__(self, path):
            self.path = path
        def convert(self, mode):
            return self
        def save(self, target, fmt, quality=100):
            SysPath(target).parent.mkdir(parents=True, exist_ok=True)
            SysPath(target).write_bytes(b"frame")

    def fake_build_vertical_strip(frames, camera_name, output_path):
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(b"strip")
        return output_path

    class FakeOllama:
        def classify_images(self, image_paths, prompt=None, *, seconds_apart=1):
            captured["seconds_apart"] = seconds_apart
            captured["image_count"] = len(image_paths)
            return {"label": "working", "confidence": 0.9, "notes": "ok"}

    monkeypatch.setattr("factory_analytics.services.fetch_frames", fake_fetch_frames)
    monkeypatch.setattr("factory_analytics.services.resize_pil_image", fake_resize)
    monkeypatch.setattr("factory_analytics.services.build_vertical_strip", fake_build_vertical_strip)
    monkeypatch.setattr(service, "frigate_client", lambda: object())
    monkeypatch.setattr(service, "ollama_client", lambda: FakeOllama())
    monkeypatch.setattr("factory_analytics.services.Image", type("FakeImageModule", (), {
        "open": staticmethod(lambda path: FakeSavedFrame(path))
    }))

    result = service._process_single_job(job)

    assert result["job"]["status"] == "success"
    assert captured["camera_name"] == "cam_interval"
    assert captured["count"] == 6
    assert captured["interval_sec"] == 0.5
    assert captured["seconds_apart"] == 0.5
    assert captured["image_count"] == 6


def test_execute_group_analysis_passes_real_capture_interval_and_prompt_timing(tmp_path: Path, monkeypatch):
    from pathlib import Path as SysPath

    from factory_analytics.services import AnalyticsService

    db = Database(path=tmp_path / "group_job_interval.db")
    service = AnalyticsService(db)
    db.update_settings({"llm_frames_per_process": 2, "llm_seconds_window": 3})

    group = db.create_group("line", "Line A", interval_seconds=60)
    camera1 = db.upsert_camera("cam_group_1", "Group Cam 1")
    camera2 = db.upsert_camera("cam_group_2", "Group Cam 2")
    db.update_camera(camera1["id"], {"enabled": True})
    db.update_camera(camera2["id"], {"enabled": True})
    db.add_camera_to_group(camera1["id"], group["id"])
    db.add_camera_to_group(camera2["id"], group["id"])
    job = db.schedule_job(camera1["id"], payload={"group_id": group["id"]}, job_type="group_analysis")

    captured = {"fetch_calls": []}

    class FakeFrame:
        def save(self, target, fmt, quality=100):
            SysPath(target).parent.mkdir(parents=True, exist_ok=True)
            SysPath(target).write_bytes(b"frame")

    def fake_fetch_frames(frigate, camera_name, count, interval_sec=1):
        captured["fetch_calls"].append((camera_name, count, interval_sec))
        return [FakeFrame() for _ in range(count)]

    def fake_resize(image, max_dim):
        return image

    class FakeSavedFrame:
        def __init__(self, path):
            self.path = path
        def convert(self, mode):
            return self
        def save(self, target, fmt, quality=100):
            SysPath(target).parent.mkdir(parents=True, exist_ok=True)
            SysPath(target).write_bytes(b"frame")

    def fake_build_vertical_strip(frames, camera_name, output_path):
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(b"strip")
        return output_path

    def fake_build_group_collage(frame_cameras, output_path):
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(b"collage")
        return output_path

    class FakeOllama:
        def classify_group_images(self, image_paths, *, seconds_apart=1, camera_count=1):
            captured["seconds_apart"] = seconds_apart
            captured["image_count"] = len(image_paths)
            captured["camera_count"] = camera_count
            return {"label": "working", "confidence": 0.95, "notes": "group ok"}

    monkeypatch.setattr("factory_analytics.services.fetch_frames", fake_fetch_frames)
    monkeypatch.setattr("factory_analytics.services.resize_pil_image", fake_resize)
    monkeypatch.setattr("factory_analytics.services.build_vertical_strip", fake_build_vertical_strip)
    monkeypatch.setattr("factory_analytics.services.build_group_collage", fake_build_group_collage)
    monkeypatch.setattr(service, "frigate_client", lambda: object())
    monkeypatch.setattr(service, "ollama_client", lambda: FakeOllama())
    monkeypatch.setattr("factory_analytics.services.Image", type("FakeImageModule", (), {
        "open": staticmethod(lambda path: FakeSavedFrame(path))
    }))

    result = service._execute_group_analysis(job, group["id"])

    assert result["ok"] is True
    assert len(captured["fetch_calls"]) == 2
    assert captured["fetch_calls"][0] == ("cam_group_1", 6, 0.5)
    assert captured["fetch_calls"][1] == ("cam_group_2", 6, 0.5)
    assert captured["seconds_apart"] == 0.5
    assert captured["image_count"] == 6
    assert captured["camera_count"] == 2


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


def test_list_segments_paginated_exposes_model_used(tmp_path: Path):
    """list_segments_paginated returns model_used computed from job result fields."""
    db = Database(path=tmp_path / "segments.db")
    camera = db.upsert_camera("cam_01", "Test Cam")
    db.update_camera(camera["id"], {"enabled": True})

    job = db.schedule_job(camera["id"], payload={"source": "test"})
    with db.connect() as conn:
        conn.execute(
            "UPDATE jobs SET raw_result = ? WHERE id = ?",
            (json.dumps({"raw": {"model": "vision-alpha"}}), job["id"]),
        )

    db.create_segment(
        job_id=job["id"],
        camera_id=camera["id"],
        start_ts="2026-04-05T12:30:00",
        end_ts="2026-04-05T12:31:00",
        label="working",
        confidence=0.95,
    )

    result = db.list_segments_paginated(page=1, page_size=10)
    assert len(result["items"]) == 1
    assert result["items"][0]["model_used"] == "vision-alpha"


def test_list_segments_exposes_evidence_frames(tmp_path: Path):
    db = Database(path=tmp_path / "segments_frames.db")
    camera = db.upsert_camera("cam_frames", "Frames Cam")
    db.update_camera(camera["id"], {"enabled": True})

    job = db.schedule_job(camera["id"], payload={"source": "test"})
    with db.connect() as conn:
        conn.execute(
            "UPDATE jobs SET raw_result = ? WHERE id = ?",
            (
                json.dumps(
                    {
                        "evidence_frames": [
                            "data/evidence/frames/cam_frames/frame_0.jpg",
                            "data/evidence/frames/cam_frames/frame_1.jpg",
                        ]
                    }
                ),
                job["id"],
            ),
        )

    db.create_segment(
        job_id=job["id"],
        camera_id=camera["id"],
        start_ts="2026-04-05T12:35:00",
        end_ts="2026-04-05T12:36:00",
        label="working",
        confidence=0.91,
        evidence_path="data/evidence/frames/cam_frames/frame_0.jpg",
    )

    result = db.list_segments(limit=10)
    assert len(result) == 1
    assert result[0]["evidence_frames"] == [
        "data/evidence/frames/cam_frames/frame_0.jpg",
        "data/evidence/frames/cam_frames/frame_1.jpg",
    ]


def test_report_daily_recent_segments_expose_model_used(tmp_path: Path):
    """report_daily recent_segments include model_used from the associated job."""
    db = Database(path=tmp_path / "report.db")
    camera = db.upsert_camera("cam_02", "Report Cam")
    db.update_camera(camera["id"], {"enabled": True})

    job = db.schedule_job(camera["id"], payload={"source": "daily"})
    with db.connect() as conn:
        conn.execute(
            "UPDATE jobs SET payload_json = ? WHERE id = ?",
            (json.dumps({"model": "report-model-v2"}), job["id"]),
        )

    db.create_segment(
        job_id=job["id"],
        camera_id=camera["id"],
        start_ts="2026-04-05T14:00:00",
        end_ts="2026-04-05T14:05:00",
        label="idle",
        confidence=0.80,
    )

    report = db.report_daily("2026-04-05")
    assert len(report["recent_segments"]) >= 1
    assert report["recent_segments"][0]["model_used"] == "report-model-v2"
