from pathlib import Path

from factory_analytics.integrations.frigate import FrigateClient


class DummyResponse:
    def __init__(self, content: bytes = b"image-bytes"):
        self.content = content

    def raise_for_status(self):
        return None

    def json(self):
        return {"cameras": {"camera_88_10": {}}}


class RecordingClient:
    def __init__(self, urls: list[str], *args, **kwargs):
        self.urls = urls

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def get(self, url):
        self.urls.append(str(url))
        return DummyResponse()


def test_fetch_latest_snapshot_requests_full_resolution_image(
    monkeypatch, tmp_path: Path
):
    requested_urls: list[str] = []

    monkeypatch.setattr(
        "factory_analytics.integrations.frigate.httpx.Client",
        lambda *a, **k: RecordingClient(requested_urls, *a, **k),
    )

    client = FrigateClient(
        {
            "frigate_url": "http://frigate.local:5000",
            "frigate_snapshot_timeout_sec": 30,
        }
    )

    destination = tmp_path / "snapshot.jpg"
    result = client.fetch_latest_snapshot("camera_88_10", destination)

    assert result == destination
    assert destination.read_bytes() == b"image-bytes"
    assert requested_urls[0] == "http://frigate.local:5000/api/config"
    assert (
        requested_urls[1] == "http://frigate.local:1984/api/frame.jpeg?src=camera_88_10"
    )
