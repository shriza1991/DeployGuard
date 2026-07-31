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
    """Build the complete semantic retrieval document for one deployment."""
    parts: list[str] = []
    pull_request = payload.get("pull_request") if isinstance(payload.get("pull_request"), dict) else {}

    _append_section(parts, "PR title", payload.get("title") or payload.get("pr_title") or pull_request.get("title"))
    _append_section(parts, "PR description", payload.get("body") or payload.get("description") or payload.get("pr_body") or pull_request.get("body"))
    commit_message = payload.get("commit_message") or payload.get("message") or payload.get("commit")
    if not commit_message and isinstance(payload.get("head_commit"), dict):
        commit_message = payload["head_commit"].get("message")
    _append_section(parts, "Commit message", commit_message)

    for file_entry in _extract_files(payload):
        if isinstance(file_entry, str):
            _append_section(parts, "Modified file", file_entry)
            continue
        if not isinstance(file_entry, dict):
            continue
        filename = next((file_entry.get(key) for key in ("filename", "name", "path", "file") if file_entry.get(key)), None)
        _append_section(parts, "Modified file", filename)
        _append_section(parts, "Git patch", file_entry.get("patch") or file_entry.get("diff"))

    for key in ("patch", "patches", "diff", "git_patches"):
        value = payload.get(key)
        if isinstance(value, list):
            for item in value:
                _append_section(parts, "Git patch", item)
        else:
            _append_section(parts, "Git patch", value)

    keywords = _detect_infrastructure_keywords("\n".join(parts))
    if keywords:
        _append_section(parts, "Detected infrastructure keywords", ", ".join(keywords))

    metadata = payload.get("metadata") if isinstance(payload.get("metadata"), dict) else {}
    for key in ("deterministic_findings", "findings"):
        _append_section(parts, "Deterministic findings", payload.get(key))
    _append_section(parts, "Deterministic findings", metadata.get("deterministic_findings"))
    for key in ("repository_context", "repository_evidence", "repository_context_chunks"):
        _append_section(parts, "Repository context", payload.get(key))
    _append_section(parts, "Repository context", metadata.get("repository_context"))

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


def _append_section(parts: list[str], label: str, value: Any) -> None:
    if value is None or value == "" or value == [] or value == {}:
        return
    rendered: list[str] = []
    _append(rendered, value)
    if rendered:
        parts.append(f"{label}:\n" + "\n".join(rendered))


def _detect_infrastructure_keywords(text: str) -> list[str]:
    keywords = (
        "dockerfile", "docker-compose", "container", "kubernetes", "deployment.yaml",
        "securitycontext", "privileged", "terraform", "helm", "github actions",
        "workflow", "iam", "security group", "ingress", "serviceaccount",
    )
    lowered = text.lower()
    return [keyword for keyword in keywords if keyword in lowered]
