from __future__ import annotations

import base64
import json
from pathlib import Path
from typing import Any
import httpx

from factory_analytics.logging_setup import setup_logging

logger = setup_logging()

SINGLE_CAMERA_PROMPT = (
    "You are a strict factory work-state auditor. Analyze the provided images conservatively and only report what is directly visible. "
    "These images are sequential frames from the SAME camera and SAME place. "
    "Each frame is approximately {seconds}s apart.\n"
    "Rules:\n"
    "1. Only use directly visible evidence.\n"
    "2. Do not infer a worker from machine motion, shadows, cloth, sacks, chairs, reflections, or hidden areas.\n"
    "3. If a person is clearly visible and actively engaged in productive physical work, use 'working'.\n"
    "4. If a person is visible but inactive or not productively engaged, use 'not_working'.\n"
    "5. If no person is clearly visible across the sequence, use 'no_person'.\n"
    "6. If evidence is weak, blocked, blurred, or ambiguous, use 'uncertain'.\n"
    "Optional: include an 'observations' array like [{\"frame_index\":0,\"label\":\"working|not_working|no_person|uncertain\",\"notes\":\"optional short note\"}] when useful. "
    "Return STRICT JSON ONLY with these exact keys:\n"
    '{"label":"working|not_working|no_person|uncertain","confidence":0.0,"notes":"short reason"}'
)

GROUP_PROMPT = (
    "You are a strict factory work-state auditor. Analyze the provided images conservatively and only report what is directly visible. "
    "Each image is a merged collage for one second in time, and each collage contains multiple labeled camera views. "
    "These collages are sequential and approximately {seconds}s apart.\n"
    "Rules:\n"
    "1. Only use directly visible evidence.\n"
    "2. If any camera clearly shows productive work in any collage, the correct final label is 'working'.\n"
    "3. If people are visible but not productively engaged, use 'not_working'.\n"
    "4. If no person is clearly visible across all collages, use 'no_person'.\n"
    "5. If evidence is weak or ambiguous, use 'uncertain'.\n"
    "Optional: include an 'observations' array like [{\"frame_index\":0,\"label\":\"working|not_working|no_person|uncertain\",\"notes\":\"optional short note\"}] when useful. "
    "Return STRICT JSON ONLY with these exact keys:\n"
    '{"label":"working|not_working|no_person|uncertain","confidence":0.0,"notes":"short reason"}'
)

VALID_LABELS = {"working", "not_working", "no_person", "uncertain"}


def normalize_label(raw_label: str) -> str | None:
    label = (raw_label or "").strip().lower().replace("-", " ")
    aliases = {
        "working": "working",
        "active": "working",
        "productive": "working",
        "not working": "not_working",
        "not_working": "not_working",
        "doing no work": "not_working",
        "idle": "not_working",
        "inactive": "not_working",
        "time pass": "not_working",
        "timepass": "not_working",
        "stopped": "not_working",
        "stopped vehicle": "not_working",
        "vehicle stopped": "not_working",
        "stopped machine": "not_working",
        "machine stopped": "not_working",
        "sleeping": "not_working",
        "sleep suspect": "not_working",
        "sleeping suspect": "not_working",
        "operator missing": "no_person",
        "operator_missing": "no_person",
        "missing operator": "no_person",
        "no operator": "no_person",
        "worker missing": "no_person",
        "missing worker": "no_person",
        "no worker": "no_person",
        "no person": "no_person",
        "no_person": "no_person",
        "no people": "no_person",
        "no human": "no_person",
        "uncertain": "uncertain",
        "unknown": "uncertain",
        "no extended analysis available": "uncertain",
        "no analysis available": "uncertain",
    }
    return aliases.get(label)


class OpenAIClient:
    def __init__(self, settings: dict[str, Any]):
        self.settings = settings
        self.base_url = (settings.get("llm_url") or "http://127.0.0.1:11434").rstrip(
            "/"
        )
        self.model = settings.get("llm_vision_model") or "qwen2.5-vl:7b"
        self.timeout = int(settings.get("llm_timeout_sec") or 120)
        self.enabled = bool(settings.get("llm_enabled", True))
        self.api_key = settings.get("llm_api_key") or ""

    def _chat_url(self) -> str:
        if self.base_url.endswith("/v1"):
            return f"{self.base_url}/chat/completions"
        return f"{self.base_url}/v1/chat/completions"

    def _models_url(self) -> str:
        if self.base_url.endswith("/v1"):
            return f"{self.base_url}/models"
        return f"{self.base_url}/v1/models"

    def health(self) -> dict[str, Any]:
        try:
            headers = {}
            if self.api_key:
                headers["Authorization"] = f"Bearer {self.api_key}"
            with httpx.Client(timeout=20, headers=headers) as client:
                r = client.get(self._models_url())
                r.raise_for_status()
                payload = r.json()
                models = [m.get("id") for m in payload.get("data", [])]
                return {"ok": True, "models": models}
        except Exception as exc:
            logger.exception("OpenAI health failed")
            return {"ok": False, "message": str(exc)}

    def _parse_classification_content(
        self, content: str, *, group_mode: bool
    ) -> dict[str, Any]:
        text = content.strip()
        if not text.startswith("{"):
            start = text.find("{")
            end = text.rfind("}")
            if start == -1 or end == -1 or end <= start:
                raise RuntimeError(
                    f"Model {self.model} did not return JSON: {content[:300]}"
                )
            text = text[start : end + 1]
        try:
            parsed = json.loads(text)
        except json.JSONDecodeError as exc:
            raise RuntimeError(
                f"Model {self.model} did not return JSON: {content[:300]}"
            ) from exc
        if group_mode and (
            parsed.get("type") == "text/html"
            or "<html" in str(parsed.get("data", "")).lower()
            or "<div" in str(parsed.get("data", "")).lower()
            or "productivity tools" in str(parsed.get("data", "")).lower()
        ):
            raise RuntimeError(
                f"Model {self.model} returned non-factory html garbage for group analysis"
            )
        if "label" not in parsed:
            raise RuntimeError(
                f"Model {self.model} returned malformed payload without label"
            )
        raw_label = parsed.get("label", "uncertain")
        label = normalize_label(raw_label)
        if label not in VALID_LABELS:
            raise RuntimeError(f"Model {self.model} returned invalid label: {raw_label}")
        try:
            confidence = float(parsed.get("confidence", 0.0))
        except (TypeError, ValueError):
            raise RuntimeError(
                f"Model {self.model} returned invalid confidence: {parsed.get('confidence')}"
            )
        if not (0.0 <= confidence <= 1.0):
            raise RuntimeError(
                f"Model {self.model} returned confidence out of range: {confidence}"
            )
        observations = []
        for item in parsed.get("observations", []):
            if not isinstance(item, dict):
                continue
            normalized = normalize_label(str(item.get("label", "")))
            if normalized not in VALID_LABELS:
                continue
            try:
                frame_index = int(item.get("frame_index", 0))
            except (TypeError, ValueError):
                continue
            observations.append(
                {
                    "frame_index": frame_index,
                    "label": normalized,
                    "notes": str(item.get("notes", "") or ""),
                }
            )
        result = {
            "label": label,
            "confidence": confidence,
            "notes": parsed.get("notes", ""),
        }
        if observations:
            result["observations"] = observations
        return result

    def _send_request(self, prompt: str, image_paths: list[Path]) -> tuple[str, Any]:
        if not self.enabled:
            raise RuntimeError("LLM client disabled in settings")
        timeout = httpx.Timeout(connect=5, read=self.timeout, write=10, pool=5)
        headers = {"Connection": "keep-alive"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        content_parts: list[dict[str, Any]] = [{"type": "text", "text": prompt}]
        for img_path in image_paths:
            image_b64 = base64.b64encode(img_path.read_bytes()).decode("utf-8")
            content_parts.append(
                {
                    "type": "image_url",
                    "image_url": {"url": f"data:image/jpeg;base64,{image_b64}"},
                }
            )
        payload = {
            "model": self.model,
            "stream": False,
            "messages": [
                {
                    "role": "system",
                    "content": "You are a JSON-only API. Return ONLY valid JSON. No reasoning, no explanation, no text outside JSON.",
                },
                {"role": "user", "content": content_parts},
            ],
        }
        with httpx.Client(timeout=timeout, headers=headers) as client:
            r = client.post(self._chat_url(), json=payload)
            r.raise_for_status()
            data = r.json()
        choices = data.get("choices") or []
        content = ""
        if choices:
            content = (choices[0].get("message") or {}).get("content", "") or ""
        if not content:
            raise RuntimeError(f"Model {self.model} returned empty response")
        return content, data

    def classify_images(
        self,
        image_paths: list[Path],
        prompt: str | None = None,
        *,
        seconds_apart: int = 1,
    ) -> dict[str, Any]:
        if not image_paths:
            raise RuntimeError("No images provided for classification")
        effective_prompt = (prompt or SINGLE_CAMERA_PROMPT).replace(
            "{seconds}", str(seconds_apart)
        )
        content, data = self._send_request(effective_prompt, image_paths)
        result = self._parse_classification_content(content, group_mode=False)
        result["raw"] = data
        result["frame_count"] = len(image_paths)
        return result

    def classify_group_images(
        self, image_paths: list[Path], *, seconds_apart: int = 1, camera_count: int = 1
    ) -> dict[str, Any]:
        if not image_paths:
            raise RuntimeError("No images provided for group classification")
        prompt = GROUP_PROMPT.replace("{count}", str(len(image_paths))).replace(
            "{seconds}", str(seconds_apart)
        )
        content, data = self._send_request(prompt, image_paths)
        result = self._parse_classification_content(content, group_mode=True)
        result["raw"] = data
        result["frame_count"] = len(image_paths)
        result["camera_count"] = camera_count
        return result

    def classify_image(
        self, image_path: Path, prompt: str | None = None
    ) -> dict[str, Any]:
        return self.classify_images([image_path], prompt)

    def classify_group_image(self, image_path: Path) -> dict[str, Any]:
        try:
            return self.classify_group_images([image_path])
        except RuntimeError as exc:
            if (
                "html garbage" not in str(exc).lower()
                and "did not return json" not in str(exc).lower()
                and "invalid boxes payload" not in str(exc).lower()
                and "malformed group payload" not in str(exc).lower()
            ):
                raise
            logger.warning(
                "Group analysis received garbage response, retrying once with strict prompt"
            )
            return self.classify_group_images([image_path])
