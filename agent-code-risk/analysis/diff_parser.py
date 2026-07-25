"""
analysis/diff_parser.py — Parse unified diff into structured DiffFile objects.

Pure text/regex — no AST, no external dependencies.
Only inspects lines; never calls the network or filesystem.

Two entry points:
  parse(payload)       — legacy: reads from raw webhook payload keys
  parse_files(files)   — primary: accepts pre-fetched GitHub PR file list
                         (use this when patches have been fetched from the GitHub API)
"""
from __future__ import annotations

import re
from typing import Any, Dict, List

from analysis.models import DiffFile

# Regex patterns for extracting structured data from diff text
_HUNK_HEADER = re.compile(r"^@@.*@@\s*(.*)", re.MULTILINE)
_PY_FUNC = re.compile(r"\bdef\s+(\w+)\s*\(")
_PY_CLASS = re.compile(r"\bclass\s+(\w+)[\s(:]")
_JS_FUNC = re.compile(r"(?:function\s+(\w+)|(?:const|let|var)\s+(\w+)\s*=\s*(?:async\s+)?(?:\(.*?\)\s*=>|\bfunction\b))")
_IMPORT_PY = re.compile(r"^\+\s*(?:import|from)\s+(\S+)")
_IMPORT_JS = re.compile(r"^\+\s*(?:import|require)\s*[\({'\"](\\S+?)['\"\\)}]")
_IMPORT_TF = re.compile(r"^\+\s*(?:module|provider)\s+[\"'](\w+)")


def parse_files(files: List[Dict[str, Any]]) -> List[DiffFile]:
    """
    Parse a pre-fetched list of GitHub PR file objects into DiffFile objects.

    This is the **primary** entry point.  Use this when files have already been
    fetched from the GitHub API (``GET /repos/{owner}/{repo}/pulls/{n}/files``)
    via ``risk_analyzers.build_analysis_context()`` or equivalent.

    Each entry is expected to be a GitHub file object with:
        filename    — relative path (required)
        status      — "added" | "modified" | "deleted" | "renamed"
        additions   — int
        deletions   — int
        patch       — unified diff string (may be absent for binary files)
    """
    diff_files: List[DiffFile] = []
    for entry in files:
        if not isinstance(entry, dict) or not entry.get("filename"):
            continue
        diff_files.append(_parse_entry(entry))
    return diff_files


def parse(payload: Dict[str, Any]) -> List[DiffFile]:
    """
    Fallback entry point: reads file list from raw webhook payload keys.

    WARNING: GitHub webhook payloads do NOT include patch text in changed_files.
    Patches must be fetched from the GitHub API first (via build_analysis_context).
    Use parse_files() instead whenever the enriched file list is available.
    """
    raw_files: List[Dict[str, Any]] = []
    for key in ("files", "changed_files", "diffs"):
        candidate = payload.get(key)
        if isinstance(candidate, list):
            for item in candidate:
                if isinstance(item, dict) and item.get("filename"):
                    raw_files.append(item)
            if raw_files:
                break

    return parse_files(raw_files)


def _parse_entry(entry: Dict[str, Any]) -> DiffFile:
    filename = str(entry.get("filename", ""))
    status = _normalise_status(str(entry.get("status", "modified")))
    additions = int(entry.get("additions") or 0)
    deletions = int(entry.get("deletions") or 0)
    patch = str(entry.get("patch") or "")

    functions_modified = _extract_functions(filename, patch)
    imports_added = _extract_imports(filename, patch)

    # If additions/deletions weren't provided, count them from the patch
    if additions == 0 and deletions == 0 and patch:
        for line in patch.splitlines():
            if line.startswith("+") and not line.startswith("+++"):
                additions += 1
            elif line.startswith("-") and not line.startswith("---"):
                deletions += 1

    return DiffFile(
        filename=filename,
        status=status,
        language="generic",            # populated by language_classifier
        additions=additions,
        deletions=deletions,
        patch=patch,
        functions_modified=functions_modified,
        imports_added=imports_added,
    )


def _normalise_status(raw: str) -> str:
    raw = raw.lower()
    mapping = {
        "added": "added",
        "removed": "deleted",
        "deleted": "deleted",
        "renamed": "renamed",
        "copied": "added",
        "modified": "modified",
        "changed": "modified",
    }
    return mapping.get(raw, "modified")


def _extract_functions(filename: str, patch: str) -> List[str]:
    """
    Extract modified function/method/class names from hunk context lines and
    added lines.  Works for Python and JavaScript/TypeScript; falls back to
    hunk header context for other languages.
    """
    found: List[str] = []
    lower = filename.lower()

    # Hunk header context (language-agnostic)
    for m in _HUNK_HEADER.finditer(patch):
        ctx = m.group(1).strip()
        if ctx:
            name = ctx.split("(")[0].split()[-1] if ctx else ""
            if name and re.match(r"\w+", name):
                found.append(name)

    # Language-specific extraction on added/context lines
    for line in patch.splitlines():
        stripped = line.lstrip("+- ")
        if lower.endswith(".py"):
            for m in _PY_FUNC.finditer(stripped):
                found.append(m.group(1))
            for m in _PY_CLASS.finditer(stripped):
                found.append(m.group(1))
        elif lower.endswith((".js", ".ts", ".jsx", ".tsx", ".mjs")):
            for m in _JS_FUNC.finditer(stripped):
                name = m.group(1) or m.group(2)
                if name:
                    found.append(name)

    seen: set = set()
    deduped: List[str] = []
    for name in found:
        if name not in seen:
            seen.add(name)
            deduped.append(name)
    return deduped[:20]


def _extract_imports(filename: str, patch: str) -> List[str]:
    """Extract newly added import statements from the patch."""
    imports: List[str] = []
    lower = filename.lower()

    for line in patch.splitlines():
        if not line.startswith("+") or line.startswith("+++"):
            continue
        if lower.endswith(".py"):
            m = _IMPORT_PY.match(line)
            if m:
                imports.append(m.group(1).split(".")[0])
        elif lower.endswith((".js", ".ts", ".jsx", ".tsx", ".mjs")):
            m = _IMPORT_JS.match(line)
            if m:
                imports.append(m.group(1))
        elif lower.endswith(".tf"):
            m = _IMPORT_TF.match(line)
            if m:
                imports.append(m.group(1))

    seen: set = set()
    deduped: List[str] = []
    for imp in imports:
        if imp not in seen:
            seen.add(imp)
            deduped.append(imp)
    return deduped
