from __future__ import annotations

import hashlib
import json
import re
from typing import Any


def clamp(value: float, minimum: float = 0.0, maximum: float = 100.0) -> int:
    return int(max(minimum, min(maximum, value)))


def stable_int_id(value: str) -> int:
    digest = hashlib.sha256(value.encode("utf-8")).hexdigest()
    return int(digest[:15], 16)


def normalized_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, default=str, separators=(",", ":"))


def build_deployment_document(payload: dict[str, Any]) -> str:
    parts: list[str] = []
    pull_request = payload.get("pull_request") if isinstance(payload.get("pull_request"), dict) else {}

    for key in ("title", "pr_title"):
        _append(parts, payload.get(key))
    _append(parts, pull_request.get("title"))

    for key in ("body", "description", "pr_body"):
        _append(parts, payload.get(key))
    _append(parts, pull_request.get("body"))

    for key in ("commit_message", "message", "commit"):
        _append(parts, payload.get(key))

    for file_entry in _extract_files(payload):
        if isinstance(file_entry, str):
            _append(parts, file_entry)
            continue
        if not isinstance(file_entry, dict):
            continue
        for key in ("filename", "name", "path", "file", "patch", "diff"):
            _append(parts, file_entry.get(key))

    for key in ("patch", "patches", "diff", "git_patches"):
        value = payload.get(key)
        if isinstance(value, list):
            for item in value:
                _append(parts, item)
        else:
            _append(parts, value)

    document = "\n".join(part for part in parts if part).lower()
    return re.sub(r"\n{3,}", "\n\n", document).strip()


def _extract_files(payload: dict[str, Any]) -> list[Any]:
    for key in ("files", "changed_files", "changedFiles"):
        value = payload.get(key)
        if isinstance(value, list):
            return value
    return []


def _append(parts: list[str], value: Any) -> None:
    if value is None:
        return
    if isinstance(value, (dict, list)):
        parts.append(normalized_json(value))
        return
    text = str(value).strip()
    if text:
        parts.append(text)

