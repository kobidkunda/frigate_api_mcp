import json
from pathlib import Path

import pytest
from PIL import Image

from factory_analytics.integrations.ollama import OllamaClient


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


def test_classify_image_requires_valid_boxes(monkeypatch, tmp_path: Path):
    image = tmp_path / "img.jpg"
    Image.new("RGB", (100, 100), color="white").save(image)
    payload = {
        "message": {
            "content": json.dumps(
                {
                    "label": "idle",
                    "confidence": 0.8,
                    "notes": "worker seated",
                    "boxes": [{"label": "person", "box": [0.1, 0.2, 0.3, 0.4]}],
                }
            )
        }
    }

    monkeypatch.setattr(
        "factory_analytics.integrations.ollama.httpx.Client",
        lambda *a, **k: DummyClient(payload),
    )
    client = OllamaClient(
        {
            "ollama_url": "http://x",
            "ollama_vision_model": "qwen3.5:9b",
            "ollama_timeout_sec": 10,
            "ollama_keep_alive": "5m",
        }
    )
    result = client.classify_image(image)
    assert result["label"] == "idle"
    assert result["boxes"][0]["label"] == "person"


def test_classify_image_fails_on_invalid_boxes(monkeypatch, tmp_path: Path):
    image = tmp_path / "img.jpg"
    Image.new("RGB", (100, 100), color="white").save(image)
    payload = {
        "message": {
            "content": json.dumps(
                {
                    "label": "idle",
                    "confidence": 0.8,
                    "notes": "worker seated",
                    "boxes": [{"label": "person", "box": [0.1, 0.2, 0.3]}],
                }
            )
        }
    }

    monkeypatch.setattr(
        "factory_analytics.integrations.ollama.httpx.Client",
        lambda *a, **k: DummyClient(payload),
    )
    client = OllamaClient(
        {
            "ollama_url": "http://x",
            "ollama_vision_model": "qwen3.5:9b",
            "ollama_timeout_sec": 10,
            "ollama_keep_alive": "5m",
        }
    )
    with pytest.raises(RuntimeError):
        client.classify_image(image)
