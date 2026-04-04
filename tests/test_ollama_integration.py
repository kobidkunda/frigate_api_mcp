import json
from pathlib import Path

import pytest
from PIL import Image

from factory_analytics.integrations.ollama import OpenAIClient


class DummyResponse:
    def __init__(self, payload):
        self._payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self._payload


class DummyClient:
    def __init__(self, payload):
        self.payload = payload

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def post(self, *args, **kwargs):
        return DummyResponse(self.payload)


class SequenceDummyClient:
    def __init__(self, payloads):
        self.payloads = list(payloads)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def post(self, *args, **kwargs):
        if not self.payloads:
            raise RuntimeError("no more payloads")
        return DummyResponse(self.payloads.pop(0))


def _openai_payload(content_str):
    return {"choices": [{"message": {"content": content_str}}]}


def test_classify_image_requires_valid_boxes(monkeypatch, tmp_path: Path):
    image = tmp_path / "img.jpg"
    Image.new("RGB", (100, 100), color="white").save(image)
    content = json.dumps(
        {
            "label": "idle",
            "confidence": 0.8,
            "notes": "worker seated",
            "boxes": [{"label": "person", "box": [0.1, 0.2, 0.3, 0.4]}],
        }
    )

    monkeypatch.setattr(
        "factory_analytics.integrations.ollama.httpx.Client",
        lambda *a, **k: DummyClient(_openai_payload(content)),
    )
    client = OpenAIClient(
        {
            "llm_url": "http://x",
            "llm_vision_model": "qwen3.5:9b",
            "llm_timeout_sec": 10,
        }
    )
    result = client.classify_image(image)
    assert result["label"] == "idle"
    assert result["boxes"][0]["label"] == "person"


def test_classify_image_fails_on_invalid_boxes(monkeypatch, tmp_path: Path):
    image = tmp_path / "img.jpg"
    Image.new("RGB", (100, 100), color="white").save(image)
    content = json.dumps(
        {
            "label": "idle",
            "confidence": 0.8,
            "notes": "worker seated",
            "boxes": [{"label": "person", "box": [0.1, 0.2, 0.3]}],
        }
    )

    monkeypatch.setattr(
        "factory_analytics.integrations.ollama.httpx.Client",
        lambda *a, **k: DummyClient(_openai_payload(content)),
    )
    client = OpenAIClient(
        {
            "llm_url": "http://x",
            "llm_vision_model": "qwen3.5:9b",
            "llm_timeout_sec": 10,
        }
    )
    with pytest.raises(RuntimeError):
        client.classify_image(image)


def test_classify_group_image_rejects_html_article_payload(monkeypatch, tmp_path: Path):
    image = tmp_path / "group.jpg"
    Image.new("RGB", (100, 100), color="white").save(image)
    content = json.dumps(
        {
            "type": "text/html",
            "data": "<div><a href='/products/2379'>The New Age of AI-Powered Productivity Tools</a></div>",
        }
    )

    monkeypatch.setattr(
        "factory_analytics.integrations.ollama.httpx.Client",
        lambda *a, **k: DummyClient(_openai_payload(content)),
    )
    client = OpenAIClient(
        {
            "llm_url": "http://x",
            "llm_vision_model": "qwen3.5:9b",
            "llm_timeout_sec": 10,
        }
    )

    with pytest.raises(RuntimeError, match="non-factory|garbage|html"):
        client.classify_group_image(image)


def test_classify_group_image_accepts_corner_coordinate_boxes(
    monkeypatch, tmp_path: Path
):
    image = tmp_path / "group_boxes.jpg"
    Image.new("RGB", (100, 100), color="white").save(image)
    content = json.dumps(
        {
            "label": "idle",
            "confidence": 0.8,
            "notes": "No people visible",
            "boxes": [
                {"label": "person", "box": [0.1, 0.2, 0.3, 0.4]},
                {"label": "person", "box": [0.36, 0.57, 0.45, 0.85]},
            ],
        }
    )

    monkeypatch.setattr(
        "factory_analytics.integrations.ollama.httpx.Client",
        lambda *a, **k: DummyClient(_openai_payload(content)),
    )
    client = OpenAIClient(
        {
            "llm_url": "http://x",
            "llm_vision_model": "qwen3.5:9b",
            "llm_timeout_sec": 10,
        }
    )

    result = client.classify_group_image(image)
    assert result["label"] == "idle"
    assert result["boxes"][1]["box"] == [0.36, 0.57, 0.45, 0.85]


def test_classify_group_image_accepts_missing_boxes_as_empty(
    monkeypatch, tmp_path: Path
):
    image = tmp_path / "group_nobox.jpg"
    Image.new("RGB", (100, 100), color="white").save(image)
    content = json.dumps({"label": "working", "confidence": 0.6})

    monkeypatch.setattr(
        "factory_analytics.integrations.ollama.httpx.Client",
        lambda *a, **k: DummyClient(_openai_payload(content)),
    )
    client = OpenAIClient(
        {
            "llm_url": "http://x",
            "llm_vision_model": "qwen3.5:9b",
            "llm_timeout_sec": 10,
        }
    )

    result = client.classify_group_image(image)
    assert result["label"] == "working"
    assert result["boxes"] == []


def test_classify_group_image_retries_after_malformed_json(monkeypatch, tmp_path: Path):
    image = tmp_path / "group_retry.jpg"
    Image.new("RGB", (100, 100), color="white").save(image)
    payloads = [
        _openai_payload('{"Camera 1 (Top Left): ":[\n    -1.0]\n    \t}'),
        _openai_payload(
            json.dumps(
                {
                    "label": "idle",
                    "confidence": 0.8,
                    "notes": "retry ok",
                    "boxes": [],
                }
            )
        ),
    ]
    client_instance = SequenceDummyClient(payloads)

    monkeypatch.setattr(
        "factory_analytics.integrations.ollama.httpx.Client",
        lambda *a, **k: client_instance,
    )
    client = OpenAIClient(
        {
            "llm_url": "http://x",
            "llm_vision_model": "qwen3.5:9b",
            "llm_timeout_sec": 10,
        }
    )

    result = client.classify_group_image(image)
    assert result["label"] == "idle"
    assert result["notes"] == "retry ok"
