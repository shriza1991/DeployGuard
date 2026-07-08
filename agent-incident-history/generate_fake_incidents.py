from __future__ import annotations

import argparse
import json
import random
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterator

from incident_seeding.models import SeedIncident

SEVERITIES = ["critical", "high", "medium", "low"]
SEVERITY_WEIGHTS = [0.20, 0.35, 0.30, 0.15]
OUTCOMES = [
    "Rollback",
    "Hotfix",
    "Incident Resolved",
    "Security Incident",
    "Production Outage",
    "Manual Intervention",
    "No Impact",
    "Partial Outage",
]
ENVIRONMENTS = ["production", "staging", "development"]
TEAMS = ["Platform", "Security", "SRE", "Data", "Payments", "Identity", "Infrastructure"]
CLOUDS = ["AWS", "GCP", "Azure", "Hybrid"]
SERVICES = [
    "Authentication API",
    "Orders Database",
    "Object Storage",
    "Kubernetes Platform",
    "CI Pipeline",
    "API Gateway",
    "Cache Layer",
    "Event Streaming",
    "Edge Network",
    "Identity Platform",
    "Build System",
    "Release Engineering",
]


@dataclass(frozen=True)
class IncidentTemplate:
    category: str
    tags: tuple[str, ...]
    title_patterns: tuple[str, ...]
    description_patterns: tuple[str, ...]
    root_cause_patterns: tuple[str, ...]
    service: str
    severity_bias: str | None = None


TEMPLATES: tuple[IncidentTemplate, ...] = (
    IncidentTemplate(
        "authentication",
        ("authentication", "security", "api"),
        (
            "Authentication middleware removed",
            "Authentication disabled in {environment}",
            "Removed auth validation from {service}",
            "Disabled login verification",
            "Auth guard deleted during deploy",
        ),
        (
            "Production deployment accidentally removed API authentication.",
            "Login verification was disabled during a config rollout.",
            "Auth middleware stopped enforcing JWT validation.",
            "OAuth callback validation was turned off in {environment}.",
        ),
        (
            "Deployment configuration error",
            "Feature flag misconfiguration",
            "Incomplete code review",
            "Environment variable mismatch",
        ),
        "Authentication API",
        "critical",
    ),
    IncidentTemplate(
        "public-storage",
        ("s3", "aws", "security", "storage"),
        (
            "Public S3 bucket detected",
            "S3 ACL set to public",
            "Bucket exposed in {environment}",
            "Public storage misconfiguration",
            "World-readable object store",
        ),
        (
            "Terraform exposed a production bucket with public-read ACL.",
            "Deployment changed bucket policy to allow anonymous listing.",
            "Backup bucket became world-readable after lifecycle update.",
            "Static assets bucket served sensitive exports.",
        ),
        (
            "Terraform ACL misconfiguration",
            "IaC drift during hotfix",
            "Policy template error",
            "Shared bucket naming mistake",
        ),
        "Object Storage",
        "critical",
    ),
    IncidentTemplate(
        "database-migration",
        ("postgres", "migration", "database"),
        (
            "Database migration failure",
            "ALTER TABLE blocked writes",
            "Schema update rollback required",
            "Migration failure during deploy",
            "Online migration timeout",
        ),
        (
            "Blocking migration locked the orders table during checkout.",
            "Long-running schema change blocked writes for 90 minutes.",
            "Column type change corrupted historical order totals.",
            "Flyway migration failed halfway through index rebuild.",
        ),
        (
            "Unsafe DDL migration",
            "Missing online migration strategy",
            "Backward incompatible migration",
            "Non-transactional DDL",
        ),
        "Orders Database",
        "high",
    ),
    IncidentTemplate(
        "kubernetes-security",
        ("kubernetes", "security", "containers"),
        (
            "Kubernetes privileged containers",
            "Privileged pod in {environment}",
            "hostPath abuse detected",
            "Host networking enabled",
            "Container escape risk identified",
        ),
        (
            "Production pod ran with privileged security context.",
            "DaemonSet granted host-level capabilities.",
            "Writable hostPath mount allowed node file tampering.",
            "Pod used hostNetwork and bypassed network policy.",
        ),
        (
            "Privileged security context enabled",
            "Helm values override",
            "Overprivileged volume mount",
            "Performance tuning side effect",
        ),
        "Kubernetes Platform",
        "critical",
    ),
    IncidentTemplate(
        "terraform",
        ("terraform", "aws", "infrastructure"),
        (
            "Terraform destroy in {environment}",
            "Terraform public resources",
            "Infrastructure drift detected",
            "Terraform state corruption",
            "IaC apply failure",
        ),
        (
            "Wrong workspace destroyed shared networking resources.",
            "Load balancer and database marked publicly accessible.",
            "Manual console change diverged from Terraform state.",
            "Concurrent applies corrupted remote state lock.",
        ),
        (
            "Terraform workspace mismatch",
            "Module default too permissive",
            "Out-of-band change",
            "Missing state locking",
        ),
        "Infrastructure",
        "high",
    ),
    IncidentTemplate(
        "secrets",
        ("secrets", "github-actions", "security"),
        (
            "Secrets committed to repository",
            "Credentials leaked in logs",
            "Secret rotation failure",
            "API key exposed in CI output",
            "Token found in container image layer",
        ),
        (
            "GitHub token was committed and appeared in build logs.",
            "Deployment script printed database password to CI output.",
            "Rotated API keys broke downstream consumers.",
            "Build artifact contained embedded credentials.",
        ),
        (
            "Secret committed to repository",
            "Verbose logging in pipeline",
            "Incomplete rotation checklist",
            "Pre-commit hook bypassed",
        ),
        "CI Pipeline",
        "critical",
    ),
    IncidentTemplate(
        "supply-chain",
        ("supply-chain", "security", "github-actions"),
        (
            "Supply chain attack detected",
            "Dependency confusion incident",
            "Compromised Docker image",
            "GitHub Actions compromise",
            "Malicious package in build",
        ),
        (
            "Compromised package exfiltrated environment variables.",
            "Build pulled similarly named malicious package.",
            "Base image contained cryptominer.",
            "Workflow used write token on untrusted pull requests.",
        ),
        (
            "Unpinned dependency",
            "Missing scope verification",
            "Unverified image tag",
            "Overprivileged workflow token",
        ),
        "Build System",
        "critical",
    ),
    IncidentTemplate(
        "deployment",
        ("kubernetes", "deployment", "outage"),
        (
            "Rolling deployment failure",
            "Blue-Green deployment failure",
            "Canary deployment failure",
            "Failed deployment in {environment}",
            "Release promotion without smoke tests",
        ),
        (
            "New pods failed readiness while old pods drained.",
            "Traffic switched to unhealthy green pool.",
            "Canary analysis ignored elevated error rate.",
            "Release job promoted artifact with failing smoke tests.",
        ),
        (
            "Readiness probe mismatch",
            "Health check endpoint stale",
            "Metric query misconfiguration",
            "Manual approval bypass",
        ),
        "Release Engineering",
        "high",
    ),
    IncidentTemplate(
        "network",
        ("network", "dns", "load-balancer"),
        (
            "Load balancer misconfiguration",
            "Ingress misconfiguration",
            "Broken health checks",
            "Missing readiness probes",
            "DNS outage in {environment}",
        ),
        (
            "Backend pool pointed to decommissioned instances.",
            "Ingress routed admin paths to public service.",
            "Health check path returned 404 causing drain.",
            "DNS TTL misconfiguration caused prolonged propagation delay.",
        ),
        (
            "Stale target group",
            "Path rule typo",
            "Health endpoint moved",
            "Incorrect record update",
        ),
        "Edge Network",
        "medium",
    ),
    IncidentTemplate(
        "resource-exhaustion",
        ("kubernetes", "memory", "outage"),
        (
            "Memory exhaustion in {environment}",
            "OOMKilled pods",
            "Disk full on node",
            "Node failure during peak",
            "Cluster autoscaler failure",
        ),
        (
            "Memory leak caused repeated pod restarts.",
            "Deployment exceeded memory limits under load.",
            "Log volume filled node disk and evicted workloads.",
            "Autoscaler could not scale due to quota limits.",
        ),
        (
            "Unbounded in-memory cache",
            "Resource limits too low",
            "Missing log rotation",
            "Cloud quota exhaustion",
        ),
        "Kubernetes Platform",
        "high",
    ),
)


def _weighted_severity(rng: random.Random, bias: str | None = None) -> str:
    if bias and rng.random() < 0.65:
        return bias
    return rng.choices(SEVERITIES, weights=SEVERITY_WEIGHTS, k=1)[0]


def _should_rollback(rng: random.Random, severity: str) -> bool:
    probability = {"critical": 0.55, "high": 0.35, "medium": 0.20, "low": 0.10}
    return rng.random() < probability.get(severity, 0.15)


def _pick_outcome(rng: random.Random, severity: str, rollback: bool) -> str:
    if rollback:
        return "Rollback"
    if severity == "critical":
        return rng.choice(["Security Incident", "Production Outage", "Manual Intervention", "Hotfix"])
    return rng.choice(OUTCOMES)


def _render(pattern: str, environment: str, service: str) -> str:
    return pattern.format(environment=environment, service=service)


def generate_incidents(
    count: int,
    *,
    start_id: int = 1000,
    seed: int | None = None,
) -> list[SeedIncident]:
    rng = random.Random(seed)
    now = datetime.now(timezone.utc)
    incidents: list[SeedIncident] = []

    for index in range(count):
        template = TEMPLATES[index % len(TEMPLATES)]
        environment = rng.choice(ENVIRONMENTS)
        service = template.service if rng.random() < 0.8 else rng.choice(SERVICES)
        severity = _weighted_severity(rng, template.severity_bias)
        rollback = _should_rollback(rng, severity)
        outcome = _pick_outcome(rng, severity, rollback)
        incident_id = f"INC-{start_id + index}"
        created_at = (now - timedelta(days=rng.randint(1, 900), hours=rng.randint(0, 23))).isoformat()

        incidents.append(
            SeedIncident(
                incident_id=incident_id,
                title=_render(rng.choice(template.title_patterns), environment, service),
                description=_render(rng.choice(template.description_patterns), environment, service),
                severity=severity,
                outcome=outcome,
                rollback=rollback,
                duration_minutes=rng.randint(10, 240),
                environment=environment,
                service=service,
                root_cause=rng.choice(template.root_cause_patterns),
                tags=list(template.tags),
                created_at=created_at,
                metadata={
                    "team": rng.choice(TEAMS),
                    "cloud": rng.choice(CLOUDS),
                    "category": template.category,
                    "synthetic": True,
                },
            )
        )

    return incidents


def iter_incident_batches(
    total: int,
    batch_size: int,
    *,
    start_id: int = 1000,
    seed: int | None = None,
) -> Iterator[list[SeedIncident]]:
    generated = 0
    batch_start = start_id
    batch_seed = seed
    while generated < total:
        size = min(batch_size, total - generated)
        batch = generate_incidents(size, start_id=batch_start, seed=batch_seed)
        yield batch
        generated += size
        batch_start += size
        batch_seed = None if batch_seed is None else batch_seed + size


def incidents_to_json(incidents: list[SeedIncident]) -> str:
    payload: list[dict[str, Any]] = [incident.payload() for incident in incidents]
    return json.dumps(payload, indent=2)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate synthetic DevSecOps incidents for Qdrant seeding.",
    )
    parser.add_argument("--count", type=int, default=500, help="Number of incidents to generate.")
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("generated_incidents.json"),
        help="Output JSON file path.",
    )
    parser.add_argument("--start-id", type=int, default=2000, help="Starting numeric incident ID suffix.")
    parser.add_argument("--seed", type=int, default=42, help="Random seed for reproducible output.")
    args = parser.parse_args()

    incidents = generate_incidents(args.count, start_id=args.start_id, seed=args.seed)
    args.output.write_text(incidents_to_json(incidents), encoding="utf-8")
    print(f"Generated {len(incidents)} incidents -> {args.output}")


if __name__ == "__main__":
    main()
