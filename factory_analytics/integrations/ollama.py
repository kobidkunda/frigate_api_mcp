from __future__ import annotations

import base64
import json
from pathlib import Path
from typing import Any
import httpx

from factory_analytics.logging_setup import setup_logging

logger = setup_logging()

DEFAULT_PROMPT = (
    "You are classifying a factory camera image. "
    "Return JSON only with keys label, confidence, notes. "
    "Allowed labels: working, idle, sleeping, uncertain, stopped, sleep-suspect. "
    "Base your answer only on visible evidence. "
    "Confidence must be a number from 0 to 1."
)

VALID_LABELS = {"working", "idle", "sleeping", "uncertain", "stopped", "sleep-suspect"}


class OllamaClient:
    def __init__(self, settings: dict[str, Any]):
        self.settings = settings
        self.base_url = (settings.get("ollama_url") or "http://127.0.0.1:11434").rstrip(
            "/"
        )
        # Allow overriding via either DB settings or environment-provided defaults
        self.model = settings.get("ollama_vision_model") or "qwen2.5-vl:7b"
        self.timeout = int(settings.get("ollama_timeout_sec") or 120)
        self.keep_alive = settings.get("ollama_keep_alive") or "5m"
        self.enabled = bool(settings.get("ollama_enabled", True))

    def _chat_url(self) -> str:
        if self.base_url.endswith("/api"):
            return f"{self.base_url}/chat"
        return f"{self.base_url}/api/chat"

    def _tags_url(self) -> str:
        if self.base_url.endswith("/api"):
            return f"{self.base_url}/tags"
        return f"{self.base_url}/api/tags"

    def health(self) -> dict[str, Any]:
        try:
            with httpx.Client(timeout=20) as client:
                r = client.get(self._tags_url())
                r.raise_for_status()
                payload = r.json()
                models = [m.get("name") for m in payload.get("models", [])]
                return {"ok": True, "models": models}
        except Exception as exc:
            logger.exception("Ollama health failed")
            return {"ok": False, "message": str(exc)}

    def classify_image(
        self, image_path: Path, prompt: str | None = None
    ) -> dict[str, Any]:
        if not self.enabled:
            raise RuntimeError("Ollama disabled in settings")
        prompt = prompt or DEFAULT_PROMPT
        image_b64 = base64.b64encode(image_path.read_bytes()).decode("utf-8")
        payload = {
            "model": self.model,
            "stream": False,
            "format": "json",
            "keep_alive": self.keep_alive,
            "messages": [{"role": "user", "content": prompt, "images": [image_b64]}],
        }
        timeout = httpx.Timeout(connect=5, read=self.timeout, write=10, pool=5)
        headers = {"Connection": "keep-alive"}
        with httpx.Client(timeout=timeout, headers=headers) as client:
            r = client.post(self._chat_url(), json=payload)
            r.raise_for_status()
            data = r.json()
        content = (((data.get("message") or {}).get("content")) or "").strip()
        if not content:
            raise RuntimeError(f"Model {self.model} returned empty response")
        try:
            parsed = json.loads(content)
            label = parsed.get("label", "uncertain")
            confidence = parsed.get("confidence", 0.0)
            if label not in VALID_LABELS:
                raise RuntimeError(
                    f"Model {self.model} returned invalid label: {label}"
                )
            try:
                confidence = float(confidence)
            except (TypeError, ValueError):
                raise RuntimeError(
                    f"Model {self.model} returned invalid confidence: {confidence}"
                )
            if not (0.0 <= confidence <= 1.0):
                raise RuntimeError(
                    f"Model {self.model} returned confidence out of range: {confidence}"
                )
            return {
                "label": label,
                "confidence": confidence,
                "notes": parsed.get("notes", ""),
                "raw": data,
            }
        except json.JSONDecodeError as exc:
            raise RuntimeError(
                f"Model {self.model} did not return JSON: {content[:300]}"
            ) from exc
