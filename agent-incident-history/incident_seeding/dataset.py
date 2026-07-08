from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

from incident_seeding.models import SeedIncident

logger = logging.getLogger("incident-history-seed")

SEVERITY_WEIGHTS: list[tuple[str, float]] = [
    ("critical", 0.20),
    ("high", 0.35),
    ("medium", 0.30),
    ("low", 0.15),
]

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

TEAMS = ["Platform", "Security", "SRE", "Data", "Payments", "Identity", "Infrastructure"]
CLOUDS = ["AWS", "GCP", "Azure", "Hybrid"]

IncidentCluster = dict[str, object]


INCIDENT_CLUSTERS: list[IncidentCluster] = [
    {
        "service": "Authentication API",
        "tags": ["authentication", "security", "api"],
        "variants": [
            ("Authentication middleware removed", "Production deployment accidentally removed API authentication.", "Deployment configuration error"),
            ("Authentication disabled", "Login verification was disabled during a config rollout.", "Feature flag misconfiguration"),
            ("Removed auth validation", "Auth guard was deleted from ingress middleware.", "Incomplete code review"),
            ("Disabled login verification", "OAuth callback validation was turned off in production.", "Environment variable mismatch"),
        ],
    },
    {
        "service": "Authentication API",
        "tags": ["authentication", "security", "bypass"],
        "variants": [
            ("Authentication bypass introduced", "A route allowed unauthenticated admin access.", "Missing authorization check"),
            ("Auth bypass via debug endpoint", "Debug endpoint exposed privileged operations.", "Debug flag left enabled"),
            ("Session validation skipped", "Session middleware short-circuited for load testing.", "Temporary bypass committed to main"),
        ],
    },
    {
        "service": "Object Storage",
        "tags": ["s3", "aws", "security", "storage"],
        "variants": [
            ("Public S3 bucket", "Terraform exposed a production bucket with public-read ACL.", "Terraform ACL misconfiguration"),
            ("S3 ACL set to public", "Deployment changed bucket policy to allow anonymous listing.", "IaC drift during hotfix"),
            ("Bucket exposed publicly", "Backup bucket became world-readable after lifecycle update.", "Policy template error"),
            ("Public storage misconfiguration", "Static assets bucket served sensitive exports.", "Shared bucket naming mistake"),
        ],
    },
    {
        "service": "Orders Database",
        "tags": ["postgres", "migration", "database"],
        "variants": [
            ("Database migration failure", "Blocking migration locked the orders table during checkout.", "Unsafe DDL migration"),
            ("ALTER TABLE outage", "Long-running schema change blocked writes for 90 minutes.", "Missing online migration strategy"),
            ("Schema update rollback", "Column type change corrupted historical order totals.", "Backward incompatible migration"),
            ("Migration failure during deploy", "Flyway migration failed halfway through index rebuild.", "Non-transactional DDL"),
        ],
    },
    {
        "service": "Customer Database",
        "tags": ["database", "security", "network"],
        "variants": [
            ("Public database endpoint", "RDS instance was reachable from the public internet.", "Public accessibility flag enabled"),
            ("Database exposed publicly", "Firewall rule opened PostgreSQL to 0.0.0.0/0.", "Emergency access rule not removed"),
            ("Open database port", "Security group allowed database access from any IP.", "Copy-paste security group"),
        ],
    },
    {
        "service": "CI Pipeline",
        "tags": ["secrets", "github-actions", "security"],
        "variants": [
            ("Secrets committed", "GitHub token was committed and appeared in build logs.", "Secret committed to repository"),
            ("Credentials in repository", "Production API key committed in test fixture.", "Pre-commit hook bypassed"),
            ("Secrets leaked in logs", "Deployment script printed database password to CI output.", "Verbose logging in pipeline"),
        ],
    },
    {
        "service": "Kubernetes Platform",
        "tags": ["kubernetes", "security", "containers"],
        "variants": [
            ("Kubernetes privileged containers", "Production pod ran with privileged security context.", "Privileged security context enabled"),
            ("Privileged pod deployment", "DaemonSet granted host-level capabilities.", "Helm values override"),
            ("Container running as root", "Image defaulted to root and wrote to host mounts.", "Dockerfile USER directive omitted"),
        ],
    },
    {
        "service": "Container Runtime",
        "tags": ["docker", "security", "container"],
        "variants": [
            ("Docker root user", "Container ran as root and modified mounted host paths.", "Dockerfile user omitted"),
            ("Container escape attempt", "Privileged container mounted docker.sock.", "Docker socket mounted"),
            ("Host networking enabled", "Pod used hostNetwork and bypassed network policy.", "Performance tuning side effect"),
            ("hostPath abuse", "Writable hostPath mount allowed node file tampering.", "Overprivileged volume mount"),
        ],
    },
    {
        "service": "Infrastructure",
        "tags": ["terraform", "aws", "outage"],
        "variants": [
            ("Terraform destroy", "Wrong workspace destroyed shared networking resources.", "Terraform workspace mismatch"),
            ("Terraform public resources", "Load balancer and database marked publicly accessible.", "Module default too permissive"),
            ("Infrastructure drift", "Manual console change diverged from Terraform state.", "Out-of-band change"),
            ("Terraform state corruption", "Concurrent applies corrupted remote state lock.", "Missing state locking"),
        ],
    },
    {
        "service": "Identity Platform",
        "tags": ["iam", "aws", "security"],
        "variants": [
            ("IAM wildcard permissions", "CI role received iam:* permissions in production.", "Wildcard IAM policy"),
            ("Overprivileged service account", "Deployment role could assume any production role.", "Trust policy too broad"),
            ("Open security groups", "Security group allowed 0.0.0.0/0 on database ports.", "Ingress rule too broad"),
        ],
    },
    {
        "service": "Data Platform",
        "tags": ["encryption", "compliance", "database"],
        "variants": [
            ("Disabled encryption", "Database snapshot created without encryption at rest.", "Encryption flag omitted"),
            ("Missing encryption at rest", "New storage class skipped KMS configuration.", "Template regression"),
            ("Certificate expiration", "TLS certificate expired on public API gateway.", "Renewal automation failure"),
            ("Expired SSL certificate", "Ingress served expired cert for 6 hours.", "Cert-manager misconfiguration"),
        ],
    },
    {
        "service": "Build System",
        "tags": ["github-actions", "security", "supply-chain"],
        "variants": [
            ("GitHub Actions compromise", "Workflow used write token on untrusted pull requests.", "Overprivileged workflow token"),
            ("Supply chain attack", "Compromised package exfiltrated environment variables.", "Unpinned dependency"),
            ("Dependency confusion", "Build pulled similarly named malicious package.", "Missing scope verification"),
            ("Compromised Docker image", "Base image contained cryptominer.", "Unverified image tag"),
        ],
    },
    {
        "service": "Cache Layer",
        "tags": ["redis", "security", "network"],
        "variants": [
            ("Redis exposed publicly", "Redis accepted unauthenticated connections from internet.", "Security group misconfiguration"),
            ("Missing backups", "Nightly backup job silently failed for two weeks.", "Monitoring gap on backup job"),
            ("Credential rotation failure", "Rotated API keys broke downstream consumers.", "Incomplete rotation checklist"),
        ],
    },
    {
        "service": "Event Streaming",
        "tags": ["kafka", "outage", "messaging"],
        "variants": [
            ("Kafka outage", "Broker disk filled and halted consumer groups.", "Retention policy misconfiguration"),
            ("Message backlog incident", "Consumer lag exceeded SLA after broker restart.", "Under-provisioned consumers"),
        ],
    },
    {
        "service": "Vector Search",
        "tags": ["qdrant", "outage", "search"],
        "variants": [
            ("Qdrant unavailable", "Vector database cluster became unreachable during rollout.", "Rolling restart without readiness gate"),
            ("Search index degradation", "Collection rebuild caused elevated query latency.", "Index maintenance during peak traffic"),
        ],
    },
    {
        "service": "API Gateway",
        "tags": ["api", "outage", "rate-limiting"],
        "variants": [
            ("Rate limiter disabled", "Rate limiting middleware was disabled globally.", "Bad feature flag default"),
            ("Webhook abuse", "Unsigned webhooks allowed replay attacks.", "Missing signature validation"),
            ("Production outage", "Gateway returned 503 for all authenticated routes.", "Upstream pool misconfiguration"),
        ],
    },
    {
        "service": "Security Operations",
        "tags": ["security", "simulation", "incident-response"],
        "variants": [
            ("Ransomware simulation misfire", "Tabletop exercise triggered real isolation runbook.", "Runbook label ambiguity"),
            ("Data corruption", "Batch job with timezone bug overwrote daily aggregates.", "Timezone conversion bug"),
        ],
    },
    {
        "service": "Kubernetes Platform",
        "tags": ["kubernetes", "memory", "outage"],
        "variants": [
            ("Memory exhaustion", "Memory leak caused repeated pod restarts.", "Unbounded in-memory cache"),
            ("OOMKilled pods", "Deployment exceeded memory limits under load.", "Resource limits too low"),
            ("Disk full", "Log volume filled node disk and evicted workloads.", "Missing log rotation"),
            ("Node failure", "Single AZ node loss reduced cluster capacity.", "Insufficient pod disruption budget"),
        ],
    },
    {
        "service": "Release Engineering",
        "tags": ["kubernetes", "deployment", "outage"],
        "variants": [
            ("Rolling deployment failure", "New pods failed readiness while old pods drained.", "Readiness probe mismatch"),
            ("Blue-Green deployment failure", "Traffic switched to unhealthy green pool.", "Health check endpoint stale"),
            ("Canary deployment failure", "Canary analysis ignored elevated error rate.", "Metric query misconfiguration"),
            ("Cluster autoscaler failure", "Autoscaler could not scale due to quota limits.", "Cloud quota exhaustion"),
        ],
    },
    {
        "service": "Edge Network",
        "tags": ["network", "dns", "load-balancer"],
        "variants": [
            ("Load balancer misconfiguration", "Backend pool pointed to decommissioned instances.", "Stale target group"),
            ("Ingress misconfiguration", "Ingress routed admin paths to public service.", "Path rule typo"),
            ("Broken health checks", "Health check path returned 404 causing drain.", "Health endpoint moved"),
            ("Missing readiness probes", "Pods received traffic before dependencies warmed.", "Probe not configured"),
            ("Broken liveness probes", "Aggressive liveness probe caused restart loop.", "Probe timeout too low"),
        ],
    },
    {
        "service": "Edge Network",
        "tags": ["dns", "cloudflare", "outage"],
        "variants": [
            ("DNS outage", "DNS TTL misconfiguration caused prolonged propagation delay.", "Incorrect record update"),
            ("Cloudflare outage", "WAF rule blocked legitimate API traffic globally.", "Overly broad WAF expression"),
        ],
    },
    {
        "service": "CI Pipeline",
        "tags": ["github-actions", "ci", "deployment"],
        "variants": [
            ("CI/CD failure", "Pipeline skipped integration tests after workflow refactor.", "GitHub Actions condition mismatch"),
            ("Failed deployment", "Release job promoted artifact with failing smoke tests.", "Manual approval bypass"),
        ],
    },
]


def _severity_for_index(index: int, total: int) -> str:
    position = index / max(total, 1)
    cumulative = 0.0
    for severity, weight in SEVERITY_WEIGHTS:
        cumulative += weight
        if position < cumulative:
            return severity
    return SEVERITY_WEIGHTS[-1][0]


def _outcome_for_variant(severity: str, rollback: bool, index: int) -> str:
    if rollback:
        return "Rollback"
    if severity == "critical":
        return OUTCOMES[index % 4]  # Rollback, Security Incident, Production Outage, Manual Intervention
    if severity == "high":
        return OUTCOMES[(index + 1) % len(OUTCOMES)]
    if severity == "medium":
        return OUTCOMES[(index + 2) % len(OUTCOMES)]
    return OUTCOMES[(index + 5) % len(OUTCOMES)]


def _should_rollback(severity: str, index: int) -> bool:
    if severity == "critical":
        return index % 2 == 0
    if severity == "high":
        return index % 3 == 0
    return index % 5 == 0


def build_curated_dataset(
    minimum: int = 50,
    maximum: int = 100,
) -> list[SeedIncident]:
    now = datetime.now(timezone.utc)
    incidents: list[SeedIncident] = []
    incident_counter = 100
    total_variants = sum(len(cluster["variants"]) for cluster in INCIDENT_CLUSTERS)  # type: ignore[arg-type]

    for cluster_index, cluster in enumerate(INCIDENT_CLUSTERS):
        service = str(cluster["service"])
        tags = [str(tag) for tag in cluster["tags"]]  # type: ignore[index]
        variants = cluster["variants"]  # type: ignore[index]
        for variant_index, (title, description, root_cause) in enumerate(variants):
            incident_counter += 1
            incident_id = f"INC-{incident_counter}"
            severity = _severity_for_index(len(incidents), total_variants)
            rollback = _should_rollback(severity, variant_index + cluster_index)
            outcome = _outcome_for_variant(severity, rollback, variant_index + cluster_index)
            environment = ("production", "staging", "development")[variant_index % 3]
            duration_minutes = 15 + ((cluster_index * 13 + variant_index * 11) % 180)
            created_at = (now - timedelta(days=7 + len(incidents) * 4, hours=variant_index * 3)).isoformat()

            incidents.append(
                SeedIncident(
                    incident_id=incident_id,
                    title=title,
                    description=description,
                    severity=severity,
                    outcome=outcome,
                    rollback=rollback,
                    duration_minutes=duration_minutes,
                    environment=environment,
                    service=service,
                    root_cause=root_cause,
                    tags=tags,
                    created_at=created_at,
                    metadata={
                        "team": TEAMS[cluster_index % len(TEAMS)],
                        "cloud": CLOUDS[variant_index % len(CLOUDS)],
                        "cluster": tags[0],
                    },
                )
            )

    if len(incidents) < minimum:
        logger.warning(
            "Curated dataset has %s incidents; expected at least %s",
            len(incidents),
            minimum,
        )

    if len(incidents) > maximum:
        incidents = incidents[:maximum]

    return incidents
