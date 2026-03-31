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
    "Return JSON only with keys label, confidence, notes, boxes. "
    "Allowed labels: working, idle, sleeping, uncertain, stopped, sleep-suspect, timepass, operator_missing. "
    "Base your answer only on visible evidence. "
    "Confidence must be a number from 0 to 1. "
    "boxes must be an array of objects with label='person' and box=[x,y,width,height] normalized from 0 to 1."
)

GROUP_PROMPT = (
    "You are classifying a merged multi-camera factory collage image. "
    "The image may contain several camera views in a grid. "
    "Analyze only visible factory/worksite scenes in the collage. "
    "Ignore any imagined webpages, articles, ads, or unrelated text. "
    "Return JSON only with keys label, confidence, notes, boxes. "
    "Allowed labels: working, idle, sleeping, uncertain, stopped, sleep-suspect, timepass, operator_missing. "
    "Base your answer only on visible evidence from the collage. "
    "Confidence must be a number from 0 to 1. "
    "boxes must be an array of objects with label='person' and box=[x,y,width,height] normalized from 0 to 1."
)

VALID_LABELS = {
    "working",
    "idle",
    "sleeping",
    "uncertain",
    "stopped",
    "sleep-suspect",
    "timepass",
    "operator_missing",
}


def normalize_label(raw_label: str) -> str | None:
    label = (raw_label or "").strip().lower().replace("-", " ")
    if label in VALID_LABELS:
        return label
    aliases = {
        "sleep suspect": "sleep-suspect",
        "sleeping suspect": "sleep-suspect",
        "time pass": "timepass",
        "timepassing": "timepass",
        "operator missing": "operator_missing",
        "missing operator": "operator_missing",
        "no operator": "operator_missing",
        "not working": "idle",
        "doing no work": "idle",
        "stopped vehicle": "stopped",
        "vehicle stopped": "stopped",
        "stopped machine": "stopped",
        "machine stopped": "stopped",
    }
    if label in aliases:
        return aliases[label]
    if "sleep" in label and "suspect" in label:
        return "sleep-suspect"
    if "time" in label and "pass" in label:
        return "timepass"
    if "operator" in label and ("missing" in label or "absent" in label):
        return "operator_missing"
    if label.startswith("stopped"):
        return "stopped"
    return None


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

    def _parse_classification_content(
        self, content: str, *, group_mode: bool
    ) -> dict[str, Any]:
        try:
            parsed = json.loads(content)
            if group_mode and (
                parsed.get("type") == "text/html"
                or "<html" in str(parsed.get("data", "")).lower()
                or "<div" in str(parsed.get("data", "")).lower()
                or "productivity tools" in str(parsed.get("data", "")).lower()
            ):
                raise RuntimeError(
                    f"Model {self.model} returned non-factory html garbage for group analysis"
                )
            if group_mode and "label" not in parsed:
                raise RuntimeError(
                    f"Model {self.model} returned malformed group payload without label"
                )
            raw_label = parsed.get("label", "uncertain")
            label = normalize_label(raw_label)
            confidence = parsed.get("confidence", 0.0)
            if label not in VALID_LABELS:
                raise RuntimeError(
                    f"Model {self.model} returned invalid label: {raw_label}"
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
            boxes = parsed.get("boxes")
            if not isinstance(boxes, list):
                logger.warning(
                    "Model %s returned non-list boxes (%s), defaulting to []",
                    self.model,
                    type(boxes).__name__,
                )
                boxes = []
            for item in boxes:
                if not isinstance(item, dict):
                    logger.warning(
                        "Model %s returned non-object box entry, skipping", self.model
                    )
                    continue
                if item.get("label") != "person":
                    logger.warning(
                        "Model %s returned non-person box label: %s, skipping",
                        self.model,
                        item.get("label"),
                    )
                    continue
                box = item.get("box")
                if not isinstance(box, list) or len(box) < 4:
                    logger.warning(
                        "Model %s returned invalid box coordinates, skipping",
                        self.model,
                    )
                    continue
                # Take first 4 values and coerce to float
                clean_box = []
                skip_box = False
                for value in box[:4]:
                    try:
                        num = float(value)
                    except (TypeError, ValueError):
                        logger.warning(
                            "Model %s returned non-numeric box coordinate: %s, skipping",
                            self.model,
                            value,
                        )
                        skip_box = True
                        break
                    clean_box.append(num)
                if skip_box:
                    continue
                # Normalize pixel coordinates to 0-1 range
                if any(v > 1.0 for v in clean_box):
                    # Looks like pixel coordinates - attempt normalization
                    max_val = max(clean_box)
                    if max_val > 0:
                        clean_box = [v / max_val for v in clean_box]
                        logger.info(
                            "Normalized box coordinates from pixel values (max=%.1f)",
                            max_val,
                        )
                # Clamp to 0-1
                clean_box = [max(0.0, min(1.0, v)) for v in clean_box]
                item["box"] = clean_box
            return {
                "label": label,
                "confidence": confidence,
                "notes": parsed.get("notes", ""),
                "boxes": boxes,
            }
        except json.JSONDecodeError as exc:
            raise RuntimeError(
                f"Model {self.model} did not return JSON: {content[:300]}"
            ) from exc

    def _classify_with_prompt(
        self, image_path: Path, prompt: str, *, group_mode: bool
    ) -> dict[str, Any]:
        if not self.enabled:
            raise RuntimeError("Ollama disabled in settings")
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
        result = self._parse_classification_content(content, group_mode=group_mode)
        result["raw"] = data
        return result

    def classify_image(
        self, image_path: Path, prompt: str | None = None
    ) -> dict[str, Any]:
        return self._classify_with_prompt(
            image_path, prompt or DEFAULT_PROMPT, group_mode=False
        )

    def classify_group_image(self, image_path: Path) -> dict[str, Any]:
        try:
            return self._classify_with_prompt(image_path, GROUP_PROMPT, group_mode=True)
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
            return self._classify_with_prompt(image_path, GROUP_PROMPT, group_mode=True)
