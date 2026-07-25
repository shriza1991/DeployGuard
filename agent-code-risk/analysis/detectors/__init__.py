"""
analysis/detectors/__init__.py

Exports a single entry point: run_all_detectors(diff_file) -> list[SecurityFinding].
Each language-specific detector module registers its rules here.
No LLM is used.
"""
from __future__ import annotations

from typing import List

from analysis.models import DiffFile, SecurityFinding
from analysis.detectors import python, docker, terraform, github_actions, kubernetes


# Map language tags to their detector modules
_DETECTOR_MAP = {
    "python":         python.detect,
    "docker":         docker.detect,
    "terraform":      terraform.detect,
    "github_actions": github_actions.detect,
    "kubernetes":     kubernetes.detect,
    # helm is also YAML-based; share the kubernetes detector
    "helm":           kubernetes.detect,
}


def run_all_detectors(diff_file: DiffFile) -> List[SecurityFinding]:
    """
    Runs the appropriate detector(s) for *diff_file* based on its language tag.

    Falls back gracefully when no detector is registered for a language.
    Never raises — detector errors are caught and logged, not propagated.
    """
    import logging
    logger = logging.getLogger("code-risk-phase1")

    detector_fn = _DETECTOR_MAP.get(diff_file.language)
    if detector_fn is None:
        return []

    try:
        return detector_fn(diff_file) or []
    except Exception as exc:
        logger.warning(
            "Detector %r failed on %r: %s",
            diff_file.language, diff_file.filename, exc
        )
        return []
