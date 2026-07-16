import io
import math
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse
from redis_store import RedisStore
from config import get_settings
from models import (
    CreateIncidentRequest,
    SimilaritySearchRequest,
)


router = APIRouter()
redis_store = RedisStore(get_settings())

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _merge_meta(decision: Dict[str, Any], meta: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """Merge webhook metadata fields into a decision dict (non-destructive)."""
    if not meta:
        return decision
    enriched = dict(decision)
    for field in ("repository", "branch", "commit_sha", "commit_message",
                  "author", "pull_request_title", "pull_request_body", "pr_user_login", "action"):
        if field in meta and field not in enriched:
            enriched[field] = meta[field]
        elif field in meta:
            # Prefer meta value if decision has empty/None
            if not enriched.get(field):
                enriched[field] = meta[field]
    return enriched


def _parse_range_days(range_str: Optional[str]) -> int:
    """Convert an AnalyticsRange string to integer days."""
    mapping = {"7d": 7, "14d": 14, "30d": 30, "90d": 90}
    return mapping.get(range_str or "7d", 7)


def _decisions_in_range(decisions: List[Dict[str, Any]], days: int) -> List[Dict[str, Any]]:
    """Filter decisions to those generated within the last `days` days."""
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    result = []
    for d in decisions:
        generated_at = d.get("generated_at", "")
        try:
            dt = datetime.fromisoformat(generated_at)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            if dt >= cutoff:
                result.append(d)
        except (ValueError, TypeError):
            # Include decisions with unparseable timestamps rather than losing them
            result.append(d)
    return result


def _compute_metrics(decisions: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Compute aggregate metrics from a list of final decisions."""
    total = len(decisions)
    safe = sum(1 for d in decisions if d.get("decision") == "SAFE")
    review = sum(1 for d in decisions if d.get("decision") == "REVIEW")
    blocked = sum(1 for d in decisions if d.get("decision") == "BLOCK")

    if total > 0:
        avg_risk = round(sum(d.get("overall_score", 0) for d in decisions) / total, 1)
        avg_conf = round(sum(d.get("overall_confidence", 0.0) for d in decisions) / total, 4)
        safe_pct = round((safe / total) * 100, 1)
        blocked_pct = round((blocked / total) * 100, 1)
    else:
        avg_risk = 0.0
        avg_conf = 0.0
        safe_pct = 0.0
        blocked_pct = 0.0

    return {
        "total": total,
        "safe": safe,
        "review": review,
        "blocked": blocked,
        "avgRisk": avg_risk,
        "avgConfidence": avg_conf,
        "safePercentage": safe_pct,
        "blockedPercentage": blocked_pct,
    }


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------

@router.get("/health")
def health_check():
    return {"status": "healthy"}


# ---------------------------------------------------------------------------
# Decision endpoint
# ---------------------------------------------------------------------------

@router.get("/decision/{correlation_id}")
def get_decision(correlation_id: str):
    """Return the final aggregated decision for a correlation_id, or 404 if not found."""
    decision = redis_store.get_final_decision(correlation_id)
    if decision:
        meta = redis_store.get_deployment_meta(correlation_id)
        return _merge_meta(decision, meta)

    # Check if aggregation is still in progress (agent results exist but no final decision yet)
    partial_results = redis_store.get_agent_results(correlation_id)
    if partial_results:
        from fastapi.responses import JSONResponse
        return JSONResponse(
            status_code=202,
            content={
                "status": "pending",
                "correlation_id": correlation_id,
                "collected_agents": list(partial_results.keys()),
                "message": "Deployment risk aggregation is in progress.",
            }
        )

    raise HTTPException(
        status_code=404,
        detail=f"No deployment found or decision expired for correlation_id: {correlation_id}",
    )


# ---------------------------------------------------------------------------
# Deployments
# ---------------------------------------------------------------------------

@router.get("/deployments")
def list_deployments(
    project: Optional[str] = None,
    since: Optional[str] = None,
    decision: Optional[str] = None,
    page: int = 1,
    page_size: int = 10,
):
    """Return a paginated list of deployment summaries from Redis."""
    all_decisions = redis_store.list_final_decisions()

    # Enrich each decision with its webhook metadata
    enriched: List[Dict[str, Any]] = []
    for d in all_decisions:
        cid = d.get("correlation_id", "")
        meta = redis_store.get_deployment_meta(cid) if cid else None
        enriched.append(_merge_meta(d, meta))

    # --- Filters ---
    filtered = enriched

    if decision:
        decision_upper = decision.upper()
        filtered = [d for d in filtered if d.get("decision", "").upper() == decision_upper]

    if project:
        project_lower = project.lower()
        filtered = [d for d in filtered if project_lower in (d.get("repository") or "").lower()]

    if since:
        try:
            since_dt = datetime.fromisoformat(since)
            if since_dt.tzinfo is None:
                since_dt = since_dt.replace(tzinfo=timezone.utc)
            filtered = [
                d for d in filtered
                if _parse_generated_at(d.get("generated_at", "")) >= since_dt
            ]
        except (ValueError, TypeError):
            pass  # Invalid since format — ignore filter

    total = len(filtered)
    start = (page - 1) * page_size
    end = start + page_size

    # Map to DeploymentSummary shape
    items = []
    for d in filtered[start:end]:
        items.append({
            "correlation_id": d.get("correlation_id", ""),
            "repository": d.get("repository", "unknown"),
            "branch": d.get("branch", ""),
            "decision": d.get("decision"),
            "overall_score": d.get("overall_score"),
            "overall_confidence": d.get("overall_confidence"),
            "severity": d.get("severity"),
            "generated_at": d.get("generated_at"),
            "status": "complete",
        })

    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
    }


def _parse_generated_at(value: str) -> datetime:
    """Parse generated_at string; return epoch on failure."""
    try:
        dt = datetime.fromisoformat(value)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except (ValueError, TypeError):
        return datetime(1970, 1, 1, tzinfo=timezone.utc)


@router.get("/deployments/metrics")
def get_metrics(
    project: Optional[str] = None,
    period: Optional[str] = None,
):
    """Return aggregate deployment metrics computed from Redis."""
    all_decisions = redis_store.list_final_decisions()

    # Filter by period if given
    if period:
        days = _parse_range_days(period)
        all_decisions = _decisions_in_range(all_decisions, days)

    # Filter by project
    if project:
        project_lower = project.lower()
        # We need meta to filter by repo name; load meta per decision
        filtered = []
        for d in all_decisions:
            cid = d.get("correlation_id", "")
            meta = redis_store.get_deployment_meta(cid) if cid else None
            repo = (meta or {}).get("repository", "") or d.get("repository", "")
            if project_lower in repo.lower():
                filtered.append(d)
        all_decisions = filtered

    return _compute_metrics(all_decisions)


@router.get("/deployments/{correlation_id}")
def get_deployment(correlation_id: str):
    """Return the full deployment detail for a correlation_id, enriched with webhook metadata."""
    decision = redis_store.get_final_decision(correlation_id)
    if not decision:
        raise HTTPException(
            status_code=404,
            detail=f"Deployment not found for correlation_id: {correlation_id}",
        )
    meta = redis_store.get_deployment_meta(correlation_id)
    enriched = _merge_meta(decision, meta)
    # Ensure status field is present
    enriched.setdefault("status", "complete")
    return enriched


# ---------------------------------------------------------------------------
# Deployment pipeline timeline (static structure — timestamps where available)
# ---------------------------------------------------------------------------

@router.get("/deployments/{correlation_id}/timeline")
def get_deployment_timeline(correlation_id: str):
    decision = redis_store.get_final_decision(correlation_id)
    generated_at = decision.get("generated_at") if decision else None

    return {
        "correlation_id": correlation_id,
        "stages": [
            {
                "id": "trigger",
                "label": "Trigger",
                "status": "completed",
                "timestamp": None,
                "details": "Webhook received by Gateway",
            },
            {
                "id": "code-analysis",
                "label": "Code Analysis",
                "status": "completed" if decision else "pending",
                "timestamp": None,
                "details": "Code Risk Agent analysis complete" if decision else "Waiting for agent",
            },
            {
                "id": "infra-scan",
                "label": "Infra Scan",
                "status": "completed" if decision else "pending",
                "timestamp": None,
                "details": "Infra Risk Agent scan complete" if decision else "Waiting for agent",
            },
            {
                "id": "incident-check",
                "label": "Incident Check",
                "status": "completed" if decision else "pending",
                "timestamp": None,
                "details": "Incident History Agent lookup complete" if decision else "Waiting for agent",
            },
            {
                "id": "decision",
                "label": "Decision",
                "status": "completed" if decision else "pending",
                "timestamp": generated_at,
                "details": f"Decision: {decision.get('decision')}" if decision else "Aggregating results",
            },
        ],
    }


# ---------------------------------------------------------------------------
# Agent status
# ---------------------------------------------------------------------------

@router.get("/agents/status")
def get_agent_status():
    import os
    import urllib.request
    import json
    
    agents = []
    
    agent_endpoints = {
        "Code Risk Agent": os.getenv("AGENT_CODE_RISK_URL", "http://agent-code-risk:8081/health"),
        "Infra Risk Agent": os.getenv("AGENT_INFRA_RISK_URL", "http://agent-infra-risk:8082/health"),
        "Incident History Agent": os.getenv("AGENT_INCIDENT_HISTORY_URL", "http://agent-incident-history:8080/health"),
    }
    
    for agent_name, url in agent_endpoints.items():
        data = None
        try:
            req = urllib.request.Request(url)
            with urllib.request.urlopen(req, timeout=2.0) as response:
                if response.status == 200:
                    data = json.loads(response.read().decode("utf-8"))
        except Exception as e:
            import logging
            logging.getLogger("uvicorn").error(f"Error querying {agent_name} at {url}: {e}")
            
        if data:
            agents.append({
                "name": agent_name,
                "status": "online",
                "latency_ms": data.get("average_latency_ms", 0.0),
                "region": "local",
                "version": data.get("version"),
                "uptime": data.get("uptime"),
                "analysis_count": data.get("analysis_count"),
                "last_run_timestamp": data.get("last_run_timestamp"),
                "average_confidence": data.get("average_confidence"),
                "cpu_usage": data.get("cpu_usage"),
                "memory_usage": data.get("memory_usage"),
            })
        else:
            agents.append({
                "name": agent_name,
                "status": "offline",
                "latency_ms": 0,
                "region": "local",
                "version": None,
                "uptime": None,
                "analysis_count": None,
                "last_run_timestamp": None,
                "average_confidence": None,
                "cpu_usage": None,
                "memory_usage": None,
            })
            
    return {"agents": agents}


# ---------------------------------------------------------------------------
# Incidents
# ---------------------------------------------------------------------------

@router.get("/incidents")
def list_incidents(
    service: Optional[str] = None,
    severity: Optional[str] = None,
    page: int = 1,
    page_size: int = 10,
):
    items = [
        {
            "incident_id": "INC-104",
            "title": "Database connection timeout",
            "description": "Customers reported 502 errors after deployment.",
            "severity": "high",
            "outcome": "Rollback completed successfully",
            "service": "inventory-service",
            "environment": "production",
            "root_cause": "Database connection pool exhaustion",
            "rollback": True,
            "timestamp": "2026-07-12T16:00:00Z",
            "tags": ["database", "rollback"],
            "metadata": {},
        }
    ]
    filtered = items
    if service:
        filtered = [i for i in filtered if i["service"] == service]
    if severity:
        filtered = [i for i in filtered if i["severity"] == severity]
    total = len(filtered)
    start = (page - 1) * page_size
    end = start + page_size
    return {"items": filtered[start:end], "page": page, "page_size": page_size, "total": total}


@router.get("/incidents/{incident_id}")
def get_incident(incident_id: str):
    if incident_id == "INC-104":
        return {
            "incident_id": "INC-104",
            "title": "Database connection timeout",
            "description": "Customers reported 502 errors after deployment.",
            "severity": "high",
            "outcome": "Rollback completed successfully",
            "service": "inventory-service",
            "environment": "production",
            "root_cause": "Database connection pool exhaustion",
            "rollback": True,
            "timestamp": "2026-07-12T16:00:00Z",
            "tags": ["database", "rollback"],
            "metadata": {},
        }
    raise HTTPException(status_code=404, detail="Incident not found")


@router.post("/incidents")
def create_incident(request: CreateIncidentRequest):
    incident = {
        "incident_id": "INC-105",
        "title": request.title,
        "description": request.description,
        "severity": request.severity,
        "outcome": request.outcome,
        "service": request.service,
        "environment": request.environment,
        "root_cause": request.root_cause,
        "rollback": request.rollback,
        "timestamp": "2026-07-13T12:30:00Z",
        "tags": request.tags or [],
        "metadata": {},
    }
    return {"incident": incident}


@router.post("/incidents/similarity")
def similarity_search(request: SimilaritySearchRequest):
    matches = [
        {
            "incident_id": "INC-104",
            "title": "Database connection timeout",
            "description": "Customers reported 502 errors after the recent deployment",
            "severity": "high",
            "outcome": "Rollback completed",
            "service": "inventory-service",
            "environment": "production",
            "similarity": 0.92,
            "timestamp": "2026-07-12T16:00:00Z",
            "root_cause": "Connection pool exhausted",
            "rollback": True,
        },
        {
            "incident_id": "INC-105",
            "title": "Authentication service failing",
            "description": "Users unable to login, 401 errors in logs",
            "severity": "critical",
            "outcome": "Rollback completed",
            "service": "auth-service",
            "environment": "production",
            "similarity": 0.88,
            "timestamp": "2026-07-13T09:30:00Z",
            "root_cause": "Token validation service down",
            "rollback": False,
        },
    ]
    return {"query": request.text, "matches": matches}


# ---------------------------------------------------------------------------
# Analytics — all computed live from Redis
# ---------------------------------------------------------------------------

def _load_all_with_meta() -> List[Dict[str, Any]]:
    """Load all final decisions and merge their webhook metadata in one pass."""
    decisions = redis_store.list_final_decisions()
    enriched = []
    for d in decisions:
        cid = d.get("correlation_id", "")
        meta = redis_store.get_deployment_meta(cid) if cid else None
        enriched.append(_merge_meta(d, meta))
    return enriched


@router.get("/analytics/summary")
def get_analytics_summary(range: Optional[str] = None):
    days = _parse_range_days(range)
    all_decisions = redis_store.list_final_decisions()

    current = _decisions_in_range(all_decisions, days)
    prior = _decisions_in_range(all_decisions, days * 2)
    # prior window = previous period (not overlapping current)
    prior_only = [d for d in prior if d not in current]

    def _trend(curr_val: float, prev_val: float) -> str:
        if curr_val > prev_val:
            return "up"
        elif curr_val < prev_val:
            return "down"
        return "flat"

    curr_m = _compute_metrics(current)
    prev_m = _compute_metrics(prior_only) if prior_only else _compute_metrics([])

    return {
        "totalAnalyzed": curr_m["total"],
        "avgRiskScore": curr_m["avgRisk"],
        "avgConfidence": curr_m["avgConfidence"],
        "totalBlocked": curr_m["blocked"],
        "trends": {
            "totalAnalyzed": {
                "value": curr_m["total"],
                "trend": _trend(curr_m["total"], prev_m["total"]),
            },
            "avgRiskScore": {
                "value": curr_m["avgRisk"],
                "trend": _trend(curr_m["avgRisk"], prev_m["avgRisk"]),
            },
            "avgConfidence": {
                "value": curr_m["avgConfidence"],
                "trend": _trend(curr_m["avgConfidence"], prev_m["avgConfidence"]),
            },
            "totalBlocked": {
                "value": curr_m["blocked"],
                "trend": _trend(curr_m["blocked"], prev_m["blocked"]),
            },
        },
    }


@router.get("/analytics/volume")


def get_analytics_volume(time_range: Optional[str] = Query(None, alias="range")):
    days = _parse_range_days(time_range)
    all_decisions = _decisions_in_range(redis_store.list_final_decisions(), days)

    # Group by UTC date
    by_date: Dict[str, Dict[str, int]] = defaultdict(
        lambda: {"safe": 0, "review": 0, "blocked": 0}
    )

    for d in all_decisions:
        try:
            dt = datetime.fromisoformat(d.get("generated_at", ""))
            date_str = dt.strftime("%Y-%m-%d")
        except (ValueError, TypeError):
            continue

        decision = d.get("decision", "")

        if decision == "SAFE":
            by_date[date_str]["safe"] += 1
        elif decision == "REVIEW":
            by_date[date_str]["review"] += 1
        elif decision == "BLOCK":
            by_date[date_str]["blocked"] += 1

    # Fill missing days
    now = datetime.now(timezone.utc)
    data = []

    for i in range(days - 1, -1, -1):
        date_str = (now - timedelta(days=i)).strftime("%Y-%m-%d")
        counts = by_date.get(
            date_str,
            {"safe": 0, "review": 0, "blocked": 0},
        )
        data.append(
            {
                "date": date_str,
                **counts,
            }
        )

    return {
        "time_range": time_range or "7d",
        "data": data,
    }


@router.get("/analytics/decisions")
def get_analytics_decisions(range: Optional[str] = None):
    days = _parse_range_days(range)
    all_decisions = _decisions_in_range(redis_store.list_final_decisions(), days)

    distribution = {"SAFE": 0, "REVIEW": 0, "BLOCK": 0}
    for d in all_decisions:
        decision = d.get("decision", "").upper()
        if decision in distribution:
            distribution[decision] += 1

    return {"range": range or "7d", "distribution": distribution}


@router.get("/analytics/blocks")
def get_analytics_blocks(
    range: Optional[str] = None,
    severity: Optional[str] = None,
    search: Optional[str] = None,
    page: int = 1,
    page_size: int = 10,
):
    days = _parse_range_days(range)
    all_decisions = _load_all_with_meta()
    in_range = _decisions_in_range(all_decisions, days)

    # Filter to BLOCK decisions only
    blocks = [d for d in in_range if d.get("decision", "").upper() == "BLOCK"]

    # Apply severity filter (maps to the overall severity field)
    if severity:
        severity_upper = severity.upper()
        blocks = [b for b in blocks if (b.get("severity") or "").upper() == severity_upper]

    # Apply search filter (matches repository name)
    if search:
        search_lower = search.lower()
        blocks = [b for b in blocks if search_lower in (b.get("repository") or "").lower()]

    total = len(blocks)
    start = (page - 1) * page_size
    end = start + page_size

    items = []
    for b in blocks[start:end]:
        agents = b.get("agents") or {}

        def _agent_score(name: str) -> int:
            agent_data = agents.get(name) or {}
            return int(agent_data.get("score", 0))

        items.append({
            "correlation_id": b.get("correlation_id", ""),
            "time": b.get("generated_at", ""),
            "repository": b.get("repository", "unknown"),
            "risk_score": b.get("overall_score", 0),
            "primary_threat": b.get("severity", "UNKNOWN"),
            "decision": b.get("decision", "BLOCK"),
            "agent_scores": {
                "code_risk": _agent_score("code-risk"),
                "infra_risk": _agent_score("infra-risk"),
                "incident_risk": _agent_score("incident-history"),
            },
            "details": b.get("summary", ""),
            "recommendations": b.get("recommendations", []),
        })

    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@router.get("/analytics/export")
def export_analytics(format: str = "csv", range: Optional[str] = None):
    """Export analytics data as CSV computed from live Redis decisions."""
    days = _parse_range_days(range)
    all_decisions = _decisions_in_range(redis_store.list_final_decisions(), days)
    metrics = _compute_metrics(all_decisions)

    csv_lines = [
        "correlation_id,repository,decision,overall_score,overall_confidence,severity,generated_at"
    ]
    all_with_meta = _load_all_with_meta()
    in_range = _decisions_in_range(all_with_meta, days)
    for d in in_range:
        row = ",".join([
            _csv_escape(d.get("correlation_id", "")),
            _csv_escape(d.get("repository", "")),
            _csv_escape(d.get("decision", "")),
            str(d.get("overall_score", 0)),
            str(d.get("overall_confidence", 0.0)),
            _csv_escape(d.get("severity", "")),
            _csv_escape(d.get("generated_at", "")),
        ])
        csv_lines.append(row)

    csv_content = "\n".join(csv_lines) + "\n"
    return StreamingResponse(
        io.StringIO(csv_content),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=analytics.csv"},
    )


def _csv_escape(value: str) -> str:
    """Wrap CSV field in quotes if it contains commas or quotes."""
    if "," in value or '"' in value:
        return '"' + value.replace('"', '""') + '"'
    return value


# ---------------------------------------------------------------------------
# Legacy test endpoint (keep to avoid breaking any existing callers)
# ---------------------------------------------------------------------------

@router.get("/test123")
def test123():
    return {"ok": True}
