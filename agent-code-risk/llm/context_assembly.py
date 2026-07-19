from typing import List, Dict, Any, Optional
import os

class Evidence:
    def __init__(self, text: str, source: str, metadata: Dict[str, Any]):
        self.text = text
        self.source = source  # e.g., "repository"
        self.metadata = metadata  # contains file_path, lines, kind, score, repo, branch

class AssembledContext:
    def __init__(
        self,
        score: int,
        severity: str,
        confidence: int,
        reasons: List[str],
        recommendations: List[str],
        changed_files: List[Dict[str, Any]],
        metadata: Dict[str, Any],
        pr_title: str = "",
        pr_description: str = "",
        commit_message: str = "",
        repository: str = "unknown",
        branch: str = "main",
        evidence_list: List[Evidence] = None
    ):
        self.score = score
        self.severity = severity
        self.confidence = confidence
        self.reasons = reasons or []
        self.recommendations = recommendations or []
        self.changed_files = changed_files or []
        self.metadata = metadata or {}
        self.pr_title = pr_title
        self.pr_description = pr_description
        self.commit_message = commit_message
        self.repository = repository
        self.branch = branch
        self.evidence_list = evidence_list or []

def assemble_context(
    payload: Dict[str, Any],
    deterministic_result: Dict[str, Any],
    raw_evidence: List[Dict[str, Any]],
    metrics: Dict[str, Any]
) -> AssembledContext:
    """
    Assembles evidence and metadata from the deployment event, deterministic findings,
    and repository context service. Enforces truncation and count limits.
    """
    pull_request = payload.get("pull_request") or {}
    pr_title = pull_request.get("title") or ""
    pr_description = pull_request.get("body") or ""
    
    head_commit = payload.get("head_commit") or {}
    commit_message = head_commit.get("message") or ""

    repo_obj = payload.get("repository") or {}
    repo_full_name = repo_obj.get("name") or repo_obj.get("full_name") or "unknown"
    repository = repo_full_name.split("/")[-1]
    branch = pull_request.get("head", {}).get("ref") or "main"

    changed_files = []
    files = payload.get("files") or []
    for f in files:
        if isinstance(f, dict):
            changed_files.append(f)

    # Process raw evidence, limiting to top 10 chunks
    evidence_objects: List[Evidence] = []
    character_budget = int(os.getenv("MAX_CONTEXT_CHARACTERS", "4000"))
    current_char_count = 0
    truncated = False

    for chunk in raw_evidence[:10]:
        chunk_meta = chunk.get("metadata") or {}
        text = chunk.get("text") or ""
        
        file_path = chunk_meta.get("relative_path") or chunk_meta.get("file_path") or "unknown"
        start_line = chunk_meta.get("start_line", 0)
        end_line = chunk_meta.get("end_line", 0)
        kind = chunk_meta.get("kind") or "source"
        score = chunk.get("score")

        # Format evidence block prefix
        lines_str = f"{start_line}-{end_line}"
        score_str = f"{score:.2f}" if score is not None else "N/A"
        
        prefix = (
            f"File: {file_path}\n"
            f"Lines: {lines_str}\n"
            f"Kind: {kind}\n"
            f"Similarity: {score_str}\n"
            f"Evidence:\n"
        )
        suffix = "\n\n"

        # Check budget
        block_len_without_text = len(prefix) + len(suffix)
        if current_char_count + block_len_without_text > character_budget:
            truncated = True
            break

        remaining_text_budget = character_budget - (current_char_count + block_len_without_text)
        
        if len(text) <= remaining_text_budget:
            # Entire block fits
            current_char_count += block_len_without_text + len(text)
            evidence_objects.append(
                Evidence(
                    text=text,
                    source="repository",
                    metadata={
                        "file_path": file_path,
                        "lines": lines_str,
                        "kind": kind,
                        "score": score,
                        "repository": repository,
                        "branch": branch
                    }
                )
            )
        else:
            # Needs truncation
            truncated_text = text[:remaining_text_budget - len("[TRUNCATED]\n")] + "\n[TRUNCATED]"
            current_char_count += block_len_without_text + len(truncated_text)
            truncated = True
            evidence_objects.append(
                Evidence(
                    text=truncated_text,
                    source="repository",
                    metadata={
                        "file_path": file_path,
                        "lines": lines_str,
                        "kind": kind,
                        "score": score,
                        "repository": repository,
                        "branch": branch
                    }
                )
            )
            break

    # Update metrics in-place
    metrics["total_characters"] = current_char_count
    metrics["context_truncated"] = truncated

    return AssembledContext(
        score=int(deterministic_result.get("score", 0)),
        severity=str(deterministic_result.get("severity", "low")),
        confidence=float(deterministic_result.get("confidence", 0.0)),
        reasons=list(deterministic_result.get("reasons", [])) or [],
        recommendations=list(deterministic_result.get("recommendations", [])) or [],
        changed_files=changed_files,
        metadata=deterministic_result.get("metadata", {}),
        pr_title=pr_title,
        pr_description=pr_description,
        commit_message=commit_message,
        repository=repository,
        branch=branch,
        evidence_list=evidence_objects
    )
