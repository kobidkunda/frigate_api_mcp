from __future__ import annotations

import base64
import json
from pathlib import Path
from typing import Any
import httpx

from factory_analytics.logging_setup import setup_logging

logger = setup_logging()

SINGLE_CAMERA_PROMPT = (
    "You are a strict factory CCTV vision auditor. Analyze the provided images conservatively and only report what is directly visible. "
    "These frames were captured {seconds}s apart from the same camera.\n"
    "CRITICAL RULES:\n"
    "1. NEVER assume a person is present unless a human head, torso, limbs, or clear body shape is actually visible.\n"
    "2. NEVER mark 'sleeping' unless a clearly visible person is seen in a sleep-like posture.\n"
    "3. Machine activity does NOT imply human presence.\n"
    "4. Bags, cloth, sacks, chairs, shadows, machine parts, reflections, and colored objects must NOT be treated as people.\n"
    "5. If no person is clearly visible, output: person_present=false, person_count=0, sleeping=false, idle=false, worker_state='no_person_visible'\n"
    "6. If visibility is poor or evidence is weak, use 'unknown' instead of guessing.\n"
    "7. Be conservative. False positives are worse than false negatives.\n\n"
    "Common false positives in this factory: cloth bundles, sacks, chairs, machine handles, colored plastic rolls, shadows, reflections, stacked material. "
    "These must NOT be classified as people.\n\n"
    "Return STRICT JSON ONLY with these exact keys:\n"
    '{"label": "working|idle|sleeping|uncertain|stopped|sleep-suspect|timepass|operator_missing", "confidence": 0.0, "notes": "brief explanation", "boxes": []}\n'
    "Allowed labels: working, idle, sleeping, uncertain, stopped, sleep-suspect, timepass, operator_missing. "
    "If no person visible in any frame, use label='operator_missing'. "
    "Confidence must be a number from 0 to 1. "
    "boxes must be an array of objects with label='person' and box=[x,y,width,height] normalized from 0 to 1. "
    "DO NOT include any text before or after the JSON. Return ONLY valid JSON."
)

GROUP_PROMPT = (
    "You are a strict factory CCTV vision auditor. Analyze the provided images conservatively and only report what is directly visible. "
    "Each image shows ALL cameras merged together for one moment in time. "
    "These {count} frames were captured {seconds}s apart.\n"
    "The labeled areas in each image show camera names for each section.\n"
    "CRITICAL RULES:\n"
    "1. NEVER assume a person is present unless a human head, torso, limbs, or clear body shape is actually visible.\n"
    "2. NEVER mark 'sleeping' unless a clearly visible person is seen in a sleep-like posture.\n"
    "3. Machine activity does NOT imply human presence.\n"
    "4. Bags, cloth, sacks, chairs, shadows, machine parts, reflections, and colored objects must NOT be treated as people.\n"
    "5. If no person is clearly visible, output: person_present=false, person_count=0, sleeping=false, idle=false, worker_state='no_person_visible'\n"
    "6. If visibility is poor or evidence is weak, use 'unknown' instead of guessing.\n"
    "7. Be conservative. False positives are worse than false negatives.\n\n"
    "Common false positives in this factory: cloth bundles, sacks, chairs, machine handles, colored plastic rolls, shadows, reflections, stacked material. "
    "These must NOT be classified as people.\n\n"
    "Return STRICT JSON ONLY with these exact keys:\n"
    '{"label": "working|idle|sleeping|uncertain|stopped|sleep-suspect|timepass|operator_missing", "confidence": 0.0, "notes": "brief explanation", "boxes": []}\n'
    "Allowed labels: working, idle, sleeping, uncertain, stopped, sleep-suspect, timepass, operator_missing. "
    "If no person visible in any camera view across all frames, use label='operator_missing'. "
    "Confidence must be a number from 0 to 1. "
    "boxes must be an array of objects with label='person' and box=[x,y,width,height] normalized from 0 to 1. "
    "DO NOT include any text before or after the JSON. Return ONLY valid JSON."
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
        "worker missing": "operator_missing",
        "missing worker": "operator_missing",
        "no worker": "operator_missing",
        "no person": "operator_missing",
        "not working": "idle",
        "doing no work": "idle",
        "stopped vehicle": "stopped",
        "vehicle stopped": "stopped",
        "stopped machine": "stopped",
        "machine stopped": "stopped",
        "no extended analysis available": "uncertain",
        "no analysis available": "uncertain",
        "no people": "operator_missing",
        "no human": "operator_missing",
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
        # Extract JSON from mixed response (model may include reasoning text)
        if not text.startswith("{"):
            start = text.find("{")
            end = text.rfind("}")
            if start != -1 and end != -1 and end > start:
                text = text[start : end + 1]
            else:
                raise RuntimeError(
                    f"Model {self.model} did not return JSON: {content[:300]}"
                )
        try:
            parsed = json.loads(text)
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
                if any(v > 1.0 for v in clean_box):
                    max_val = max(clean_box)
                    if max_val > 0:
                        clean_box = [v / max_val for v in clean_box]
                        logger.info(
                            "Normalized box coordinates from pixel values (max=%.1f)",
                            max_val,
                        )
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
        if len(image_paths) == 1:
            effective_prompt = prompt or SINGLE_CAMERA_PROMPT
        else:
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
