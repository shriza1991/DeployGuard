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
            ("OAuth scope validation omitted", "API allowed read-only tokens to invoke write endpoints.", "Improper scope mapping check"),
            ("Bearer token parsing failure", "Empty Authorization header led to null-pointer error in auth middleware.", "Missing null-check on token extraction"),
            ("JWT signature validation disabled", "Authentication filter accepted tokens signed with 'none' algorithm.", "Insecure library default configuration"),
            ("Unbounded token storage", "Old OAuth tokens did not expire in redis backend, exhausting cache memory.", "Missing TTL on token creation"),
        ],
    },
    {
        "service": "Authentication API",
        "tags": ["authentication", "security", "bypass"],
        "variants": [
            ("Authentication bypass introduced", "A route allowed unauthenticated admin access.", "Missing authorization check"),
            ("Auth bypass via debug endpoint", "Debug endpoint exposed privileged operations.", "Debug flag left enabled"),
            ("Session validation skipped", "Session middleware short-circuited for load testing.", "Temporary bypass committed to main"),
            ("Bypass via header spoofing", "Ingress did not strip incoming X-User-Id header, allowing user impersonation.", "Insecure ingress proxy configuration"),
            ("Bypass via duplicate parameter", "Duplicate user parameters in querystring bypassed verification checks.", "Query parameter pollution handling bug"),
            ("Path traversal auth bypass", "URL double-encoding bypassed regex path checks in firewall.", "Normalized path validation failure"),
            ("SQL injection in auth handler", "Raw SQL query in authenticate endpoint bypassed login via tautology.", "Unsanitized user input formatting"),
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
            ("Unencrypted bucket creation", "New logging bucket created without default KMS encryption.", "Omission of aws_s3_bucket_server_side_encryption_configuration"),
            ("Bucket CORS policy wildcard", "S3 CORS configuration allowed all origins (*) on internal data bucket.", "Overly permissive CORS configuration"),
            ("Missing bucket versioning", "Accidental mass deletion of objects due to missing S3 versioning configuration.", "Versioning flag disabled in Terraform"),
            ("Object ownership takeover", "Objects written by external accounts were inaccessible to the bucket owner.", "Missing bucket-owner-full-control ACL enforcement"),
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
            ("Constraint creation lockout", "Adding NOT NULL constraint without DEFAULT locked the table.", "Missing migration pre-validation"),
            ("Foreign key creation timeout", "Validating new FK constraint blocked concurrent row inserts.", "Missing NOT VALID migration step"),
            ("Migration lock timeout", "Deadlock during migration run aborted deployment rollouts.", "High-concurrency contention on migration table"),
            ("Primary key sequence overflow", "Serial primary key reached maximum value, blocking new order creation.", "Integer type limits reached"),
        ],
    },
    {
        "service": "Customer Database",
        "tags": ["database", "security", "network"],
        "variants": [
            ("Public database endpoint", "RDS instance was reachable from the public internet.", "Public accessibility flag enabled"),
            ("Database exposed publicly", "Firewall rule opened PostgreSQL to 0.0.0.0/0.", "Emergency access rule not removed"),
            ("Open database port", "Security group allowed database access from any IP.", "Copy-paste security group"),
            ("RDS public subnets association", "DB subnet group associated with internet-routable subnets.", "IaC module networking error"),
            ("Missing database TLS verification", "Application connected to PostgreSQL without sslmode=verify-full.", "TLS validation disabled in connection string"),
            ("SSL cert verification bypass", "Connection string configured to ignore DB certificate authority validation.", "Permissive sslmode setting in staging config"),
            ("Exposed database snapshot", "RDS database snapshot shared with unauthorized external accounts.", "Incorrect AWS KMS key sharing permissions"),
        ],
    },
    {
        "service": "CI Pipeline",
        "tags": ["secrets", "github-actions", "security"],
        "variants": [
            ("Secrets committed", "GitHub token was committed and appeared in build logs.", "Secret committed to repository"),
            ("Credentials in repository", "Production API key committed in test fixture.", "Pre-commit hook bypassed"),
            ("Secrets leaked in logs", "Deployment script printed database password to CI output.", "Verbose logging in pipeline"),
            ("AWS keys leaked in CI artifacts", "Workflow uploaded build directory containing cached AWS credentials.", "Incomplete gitignore pattern in build workspace"),
            ("Slack webhook token exposed", "Slack notification integration token committed in cleartext.", "Hardcoded secret in pipeline notification step"),
            ("Docker hub credential leak", "Build logs printed registry password during docker login failure.", "Missing mask validation in third-party runner action"),
            ("Git history credentials exposure", "Sensitive SSH key was pushed in a temporary branch git history.", "Improper branch cleanup before push"),
        ],
    },
    {
        "service": "Kubernetes Platform",
        "tags": ["kubernetes", "security", "containers"],
        "variants": [
            ("Kubernetes privileged containers", "Production pod ran with privileged security context.", "Privileged security context enabled"),
            ("Privileged pod deployment", "DaemonSet granted host-level capabilities.", "Helm values override"),
            ("Container running as root", "Image defaulted to root and wrote to host mounts.", "Dockerfile USER directive omitted"),
            ("HostPath volume mount abuse", "Pod mounted host root directory allowing read/write host filesystem access.", "Insecure pod configuration allowed by namespace policy"),
            ("Default namespace service account leak", "System allowed pods to automount default ServiceAccount tokens unnecessarily.", "automountServiceAccountToken not disabled"),
            ("Missing network policy boundaries", "Internal test pods could reach sensitive metadata endpoints on nodes.", "No default-deny egress NetworkPolicy applied"),
            ("Kubernetes dashboard exposed", "Dashboard was deployed without authentication on public ingress.", "Ingress service configuration error"),
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
            ("Container capabilities escalation", "Container ran with CAP_SYS_ADMIN enabled.", "Explicit capabilities override in pod spec"),
            ("Docker daemon socket exposure", "ReadOnly mount of docker.sock allowed container to manage host container engine.", "Insecure volumes mapping"),
            ("Shared IPC namespace", "Pod configured with hostIPC=true allowed container to inspect host process memory.", "Debugging configuration left in production"),
            ("Unrestricted PID namespace sharing", "Pod deployed with hostPID=true exposing host processes to container.", "Improper pod security standard validation"),
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
            ("Terraform resource rename cycle", "Renaming key resource without lifecycle block forced recreation of production DB.", "Missing prevent_destroy lifecycle rule"),
            ("AWS provider version mismatch", "Terraform apply failed due to unsupported argument in deprecated provider version.", "Incomplete lock file synchronization"),
            ("Terraform parallel execution failure", "Rate limits hit from cloud provider during massive parallel apply.", "High concurrency count flag used in pipeline"),
            ("Terraform remote backend lockout", "S3 bucket configuration drift prevented reading state file.", "Backend bucket policy update restriction"),
        ],
    },
    {
        "service": "Identity Platform",
        "tags": ["iam", "aws", "security"],
        "variants": [
            ("IAM wildcard permissions", "CI role received iam:* permissions in production.", "Wildcard IAM policy"),
            ("Overprivileged service account", "Deployment role could assume any production role.", "Trust policy too broad"),
            ("Open security groups", "Security group allowed 0.0.0.0/0 on database ports.", "Ingress rule too broad"),
            ("IAM trust policy wildcard", "Assumable role trusted root account without external ID validation.", "Missing ExternalId in trust relationship"),
            ("AWS KMS wildcard key policy", "Key policy allowed administrative permissions to all principals in account.", "Permissive key policy template"),
            ("Overprivileged AWS IAM user", "Developer user policy included iam:PassRole without resource boundaries.", "Missing permission boundaries on developer IAM role"),
            ("IAM role session duration limit", "Max session duration set to 12 hours for privileged admin roles.", "Non-compliance with short-lived session standards"),
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
            ("KMS key deletion scheduled", "Production KMS key was accidentally scheduled for deletion by automation script.", "Missing IAM delete protection rules"),
            ("Expired CA intermediate", "Subordinate CA certificate expired, breaking trust chain for clients.", "Incomplete CA rollover procedure"),
            ("Let's Encrypt renewal block", "HTTP-01 validation failed due to custom firewall rules blocking ingress.", "ACME challenge path blocked by security rule"),
            ("Unencrypted EBS volumes", "Worker node launch template specified unencrypted root volumes.", "Missing encryption flag in EC2 block device mapping"),
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
            ("GitHub Actions script injection", "Workflow parsed untrusted git commit message directly into bash script.", "Unsanitized user-controlled input in run step"),
            ("Unpinned action dependency", "Workflow pulled third-party action using master tag instead of SHA digest.", "Mutable action version reference used"),
            ("Cache poisoning in CI pipeline", "Malicious PR injected compromised binary into remote dependencies cache.", "Insecure GHA workflow cache key sharing"),
            ("Poisoned wrapper script", "Build executed gradle-wrapper without verifying checksum.", "Unverified helper executable committed to repo"),
        ],
    },
    {
        "service": "Cache Layer",
        "tags": ["redis", "security", "network"],
        "variants": [
            ("Redis exposed publicly", "Redis accepted unauthenticated connections from internet.", "Security group misconfiguration"),
            ("Missing backups", "Nightly backup job silently failed for two weeks.", "Monitoring gap on backup job"),
            ("Credential rotation failure", "Rotated API keys broke downstream consumers.", "Incomplete rotation checklist"),
            ("Redis connection limit reached", "Cache clients starved due to maxclients threshold being reached.", "Missing connection reuse or pooling logic"),
            ("Redis OOM eviction failure", "Eviction policy set to noeviction caused write command failures under memory load.", "Misconfigured maxmemory-policy"),
            ("Redis replication link broken", "Stale reads from replica cache due to replication link disconnect.", "Unmonitored replication lag metrics"),
            ("Redis sentinel split brain", "Sentinel nodes isolated due to network partitioning, causing split-brain master promotion.", "Incorrect quorum size settings"),
        ],
    },
    {
        "service": "Event Streaming",
        "tags": ["kafka", "outage", "messaging"],
        "variants": [
            ("Kafka outage", "Broker disk filled and halted consumer groups.", "Retention policy misconfiguration"),
            ("Message backlog incident", "Consumer lag exceeded SLA after broker restart.", "Under-provisioned consumers"),
            ("Kafka broker partition offline", "Under-replicated partitions caused read/write errors on key topics.", "Unclean leader election disabled under partition loss"),
            ("Kafka schema registry mismatch", "Producer sent message with unregistered Avro schema causing consumer crashes.", "Strict schema validation bypass in client library"),
            ("Kafka coordinator rebalance storm", "Frequent consumer group rebalances caused processing stops.", "Heartbeat timeout configuration too low"),
            ("Kafka SASL authentication failure", "Incorrect client credentials blocked microservice ingestion pipeline.", "Secrets manager failed to inject correct jaas configuration"),
            ("Kafka message size limit exceeded", "Producer message rejected due to exceeding maximum request size.", "Mismatch between producer max.request.size and broker message.max.bytes"),
        ],
    },
    {
        "service": "Vector Search",
        "tags": ["qdrant", "outage", "search"],
        "variants": [
            ("Qdrant unavailable", "Vector database cluster became unreachable during rollout.", "Rolling restart without readiness gate"),
            ("Search index degradation", "Collection rebuild caused elevated query latency.", "Index maintenance during peak traffic"),
            ("Qdrant OOM during indexing", "Heavy payload update caused search node to run out of memory.", "Missing indexing memory limit bounds"),
            ("Qdrant write timeout errors", "Client requests failed due to consensus leader lock during cluster partition.", "Write quorum unsatisfied under high nodes churn"),
            ("Qdrant disk storage filled", "Index growth filled container disk space causing engine to drop writes.", "Index optimizer config threshold set too low"),
            ("Qdrant TLS handshake failure", "Internal cluster communication broken after certificate rotation.", "Missing private root CA updates in container trust store"),
            ("Qdrant metadata filter collision", "Complex filter payload structure crashed query parser.", "Type conversion bug in custom schema migration"),
        ],
    },
    {
        "service": "API Gateway",
        "tags": ["api", "outage", "rate-limiting"],
        "variants": [
            ("Rate limiter disabled", "Rate limiting middleware was disabled globally.", "Bad feature flag default"),
            ("Webhook abuse", "Unsigned webhooks allowed replay attacks.", "Missing signature validation"),
            ("Production outage", "Gateway returned 503 for all authenticated routes.", "Upstream pool misconfiguration"),
            ("API gateway timeout", "Gateway returned 504 Gateway Timeout due to slow upstream responses.", "Missing timeout settings in reverse proxy definition"),
            ("Gateway CORS preflight drop", "Preflight OPTIONS requests rejected with 400 Bad Request.", "Misconfigured CORS policy on gateway router"),
            ("API gateway header size limit", "Requests with large tokens rejected with 431 Request Header Fields Too Large.", "Gateway client buffer size settings too small"),
            ("Upstream DNS resolution failure", "Gateway failed to resolve backend service DNS during outage.", "CoreDNS service limits hit in kubernetes namespace"),
        ],
    },
    {
        "service": "Security Operations",
        "tags": ["security", "simulation", "incident-response"],
        "variants": [
            ("Ransomware simulation misfire", "Tabletop exercise triggered real isolation runbook.", "Runbook label ambiguity"),
            ("Data corruption", "Batch job with timezone bug overwrote daily aggregates.", "Timezone conversion bug"),
            ("Logging ingestion lag", "Security information and event management (SIEM) delayed alert ingestion by 2 hours.", "Log pipeline queue congestion"),
            ("Intrusion detection false positive", "IDS blocked entire backend subnet after security testing scan.", "Missing IP allowlist in IDS scanner configuration"),
            ("Audit logs parsing failure", "JSON log format change broke security parser alerts.", "Unannounced upstream logging schema change"),
            ("Vulnerability scan crash", "Automated dependency scanner crashed container registry service.", "Concurrency limits not enforced on host registry API"),
            ("Log retention policy purge", "Security audit logs deleted prematurely due to lifecycle policy rule.", "Incorrect prefix matching filter in lifecycle rule"),
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
            ("Kubelet node pressure", "Worker node marked unschedulable due to high disk inode usage.", "Unchecked tmpfs file generation in container workspace"),
            ("Pod eviction loop", "Pods constantly evicted due to ephemeral-storage limits exceeded.", "Log files written outside configured emptyDir mount limits"),
            ("CoreDNS OOMKilled", "Kubernetes DNS queries failed after CoreDNS pods ran out of memory.", "Missing cache optimization for internal domain searches"),
            ("Admission controller timeout", "Kube-apiserver failed to schedule pods because webhook call timed out.", "Admission webhook endpoint unmonitored or overloaded"),
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
            ("ArgoCD out of sync loop", "ArgoCD continuously synchronized deployment due to mutating webhook.", "IgnoreDifferences rule missing in ArgoCD application spec"),
            ("Helm release lock", "Helm deployment stuck in pending-upgrade state after crash.", "Previous upgrade command interrupted unexpectedly"),
            ("Docker image pull backoff", "Deployment failed due to private registry authentication token expiration.", "ImagePullSecrets credential renewal cron job failure"),
            ("HPA scaling crash loop", "Horizontal Pod Autoscaler caused flap due to conflicting CPU/Memory target metrics.", "Incompatible resource metric target calculation"),
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
            ("ALB Target Group connection timeout", "Load balancer returned 504 due to backend keep-alive mismatch.", "Backend server keep-alive timeout less than ALB idle timeout"),
            ("SSL/TLS handshake failure", "ALB dropped connections using older TLS protocols from clients.", "Outdated TLS security policy associated with listener"),
            ("Sticky session mismatch", "Load balancer failed to route requests to same backend due to cookie expiry.", "Session affinity cookie path parsing error"),
            ("ALB target limit reached", "New pods could not register with ALB due to target group limits.", "AWS target group registration threshold exceeded"),
        ],
    },
    {
        "service": "Edge Network",
        "tags": ["dns", "cloudflare", "outage"],
        "variants": [
            ("DNS outage", "DNS TTL misconfiguration caused prolonged propagation delay.", "Incorrect record update"),
            ("Cloudflare outage", "WAF rule blocked legitimate API traffic globally.", "Overly broad WAF expression"),
            ("Cloudflare SSL handshake error", "Cloudflare returned 525 SSL Handshake Failed for origin requests.", "Missing trusted origin certificate on backend host"),
            ("DNS record typo", "Production ingress domain updated with wrong CNAME target.", "Manual entry error in cloud console"),
            ("Stale external-dns entries", "Kubernetes external-dns failed to clean up records for deleted ingress.", "Insufficient IAM permissions for Route53 record deletion"),
            ("DNSSEC validation failure", "Domain became unreachable because DNSSEC keys were not rotated properly.", "Key signing key (KSK) mismatch with registrar record"),
            ("Cloudflare rate limiting block", "Cloudflare WAF blocked API integration client calls.", "Incorrect client IP detection via X-Forwarded-For headers"),
        ],
    },
    {
        "service": "CI Pipeline",
        "tags": ["github-actions", "ci", "deployment"],
        "variants": [
            ("CI/CD failure", "Pipeline skipped integration tests after workflow refactor.", "GitHub Actions condition mismatch"),
            ("Failed deployment", "Release job promoted artifact with failing smoke tests.", "Manual approval bypass"),
            ("GitHub Actions runner exhaustion", "Deployments delayed due to self-hosted runner queue bottleneck.", "Missing scaling policy on runner group"),
            ("Build artifact corruption", "Webpack build uploaded zero-byte bundle to CDN bucket.", "Silent compilation error ignored by upload script"),
            ("CI environment variable overwrite", "Production deployment values overwritten by staging values in runner config.", "Incorrect runner variable environment scope matching"),
            ("Docker build cache collision", "Invalidated docker cache caused deployment of outdated application version.", "Improper use of caching keys on multi-architecture builder"),
            ("Pipeline timeout", "Production build job terminated after hitting the 60 minutes limit.", "Stuck integration test suite waiting for input"),
        ],
    },
    {
        "service": "Service Mesh",
        "tags": ["istio", "mesh", "outage"],
        "variants": [
            ("Istio mTLS strict mode mismatch", "Microservice communication failed after strict mTLS enforcement.", "Missing Sidecar injection or PeerAuthentication mismatch"),
            ("Envoy sidecar memory leak", "Envoy proxy crashed due to virtual memory exhaustion.", "High volume of log parsing or trace headers aggregation"),
            ("Istio VirtualService routing loop", "HTTP requests routed infinitely between gateway and app.", "Duplicate path prefix rewrite in VirtualService match rules"),
            ("DestinationRule configuration error", "Load balancing settings caused unequal traffic distribution.", "Stale host subset definition in DestinationRule"),
            ("Istio Sidecar injection failure", "New pods started without sidecar proxy, bypassing security policies.", "Namespace label mismatch or mutating webhook failure"),
            ("Envoy rate limiting bypass", "Rate limiting filters did not apply to cross-mesh requests.", "Improperly configured EnvoyFilter path filters"),
            ("Mesh DNS resolution failure", "Services failed to resolve internal mesh endpoints.", "CoreDNS integration mismatch with Istio pilot-agent"),
            ("Istio Gateway port collision", "Ingress gateway failed to start due to port binding conflict.", "Duplicate port definition in host network settings"),
        ],
    },
    {
        "service": "Secrets Manager",
        "tags": ["vault", "secrets", "security"],
        "variants": [
            ("HashiCorp Vault token expiration", "Cron jobs failed because the injected app token expired.", "Token TTL shorter than job duration and missing renewal logic"),
            ("Vault audit log block", "Vault stopped responding to requests because the audit log path was full.", "Strict audit logging block policy enabled"),
            ("Secrets manager rotation lock", "Database password rotated but client app still used cached credentials.", "Cache expiry in client library too long"),
            ("Unencrypted ConfigMap reference", "Application config committed secrets in cleartext ConfigMaps.", "Missing encryption validation in pre-commit hooks"),
            ("Vault policy privilege escalation", "Read-only role policy allowed writing to secret storage engine.", "Incorrect wildcard matching in HCL path policy"),
            ("AWS Secrets Manager throttling", "Kubernetes CSI driver rate-limited during cluster scaling.", "High-frequency fetching of secrets without caching"),
            ("Ansible Vault decryption failure", "Ansible playbook execution aborted due to missing vault key.", "Secrets file unreadable in CI runner environment"),
            ("Secret engine mount conflict", "Deploy script failed to mount key-value store at existing path.", "Non-idempotent terraform apply script"),
        ],
    },
    {
        "service": "Networking Gateway",
        "tags": ["network", "routing", "outage"],
        "variants": [
            ("NAT Gateway port exhaustion", "Outgoing API calls failed due to SNAT port exhaustion under peak load.", "Insufficient NAT Gateways for scale of worker nodes"),
            ("Transit Gateway routing loop", "VPC traffic dropped due to cyclic routes in Transit Gateway route tables.", "Manual route override in core routing table"),
            ("VPN Tunnel disconnect", "On-premise database replication halted due to IPSec tunnel disconnect.", "BGP session timeout or key regeneration mismatch"),
            ("VPC CIDR block exhaustion", "No new worker nodes could be provisioned in private subnets.", "CIDR allocation block too small for scaling requirements"),
            ("VPC Peering routing error", "Subnet routes not updated after peering link reconstruction.", "Terraform module did not update peer route tables"),
            ("Direct Connect routing flap", "Traffic latency spiked due to routing path flapping between DC and VPN fallback.", "Inconsistent AS path prepending on fallback router"),
            ("DNS routing conflict", "Private hosted zone routing shadowed public domain endpoints.", "Overlapping domain name registration in Route53"),
            ("Security group ingress limit", "Could not apply firewall update due to hitting AWS security group rule limit.", "High number of individual IP ingress rules instead of CIDR blocks"),
        ],
    },
    {
        "service": "Observability Collector",
        "tags": ["monitoring", "prometheus", "outage"],
        "variants": [
            ("Prometheus cardinality explosion", "Prometheus server ran out of memory and crashed.", "High cardinality labels introduced in custom application metrics"),
            ("Vector log agent CPU throttling", "Log ingestion delayed due to high CPU usage in forwarder.", "Inefficient regex parsing rules applied to raw application logs"),
            ("OpenTelemetry collector packet drops", "Traces dropped due to collector queue buffer overflow.", "Downstream APM backend latency or insufficient collector buffer size"),
            ("Prometheus scraper timeout", "Target metrics missing from dashboard due to slow scrape response.", "Exporter response time exceeding scraper timeout settings"),
            ("Grafana dashboard query deadlock", "Grafana dashboards failed to load due to database connection exhaustion.", "Heavy and unoptimized SQL queries run against historical metrics store"),
            ("Datadog API quota exceeded", "Metrics submission rejected due to hitting hourly ingest limit.", "Unexpected debug logging enabled in high-volume microservices"),
            ("Log pipeline backpressure", "Log shippers stopped sending data due to Elasticsearch buffer saturation.", "Under-provisioned Elasticsearch ingest nodes"),
            ("Alert manager duplicate storm", "On-call engineers received duplicate alerts during outage.", "Alertmanager grouping rules not configured for deduplication"),
        ],
    },
    {
        "service": "Distributed Storage",
        "tags": ["storage", "pv", "outage"],
        "variants": [
            ("Persistent Volume provisioning timeout", "StatefulSet pods stuck in Pending state.", "AWS EBS volume creation limit reached or API throttling"),
            ("EBS IOPS throttling", "Database query performance degraded drastically.", "Disk throughput exceeding provisioned IOPS limit"),
            ("NFS mount lock contention", "Shared assets pod failed to write due to NFS lock timeout.", "High concurrency file write lock conflict in media processor"),
            ("Persistent Volume read-only mount", "Pod started but could not write to disk.", "Volume dirty bit set or storage backend hardware failure"),
            ("StorageClass mapping mismatch", "Helm deployment failed to locate matching dynamic storage class.", "Storage provider name changed during cluster upgrade"),
            ("EFS burst credit exhaustion", "Shared media portal crashed due to read/write speed drop.", "Unmonitored burst credit usage on low-throughput file system"),
            ("PVC size expansion failure", "Resizing volume failed because cloud provider storage backend did not support online expansion.", "Incorrect AllowVolumeExpansion setting in StorageClass"),
            ("Snapshot creation failure", "Volume snapshots failed to complete, breaking backup pipeline.", "Underlying disk read error or API rate limiting"),
        ],
    },
    {
        "service": "Load Balancer",
        "tags": ["alb", "network", "outage"],
        "variants": [
            ("HTTP/2 protocol error", "Web browser requests failed with HTTP/2 stream errors.", "Incompatible ALPN negotiation on backend proxy"),
            ("SSL handshake timeout", "Mobile client requests dropped under heavy traffic load.", "ALB CPU exhaustion or missing session ticket cache configuration"),
            ("Sticky session cookie expiry", "Users logged out repeatedly due to sticky session expiration mismatch.", "ALB cookie duration set shorter than application session duration"),
            ("NLB target registration mismatch", "Network Load Balancer routed traffic to dead pods.", "Target group IP registration mismatch during rolling update"),
            ("ALB path prefix routing error", "API gateway returned 404 for certain routes.", "Regex path priority rule order in listener configuration"),
            ("Connection multiplexing failure", "High latency due to upstream backend connection reuse exhaustion.", "Max requests per connection limit reached in proxy configuration"),
            ("Cross-zone load balancing disabled", "Traffic routed unevenly across availability zones.", "Cross-zone load balancing flag set to false in Terraform"),
            ("HTTP header size limit exceeded", "Gateway returned 400 Bad Request to clients with large headers.", "Backend buffer size smaller than ALB limit"),
        ],
    },
    {
        "service": "Database Replica",
        "tags": ["database", "replication", "outage"],
        "variants": [
            ("PostgreSQL replica lag", "Read queries returned stale data.", "High volume write transaction blocking replication stream"),
            ("Replication slot exhaustion", "Primary database stopped replicating, filling master disk with WAL segments.", "Inactive or dead replication slot not deleted"),
            ("Read-only query conflict", "Long-running queries on replica cancelled due to conflict with recovery.", "max_standby_streaming_delay set too low on standby node"),
            ("Failover cluster partition split-brain", "Two database nodes claimed to be primary master.", "Consensus heartbeat timeout too low under network congestion"),
            ("Logical replication deserialization failure", "Replica crash loop due to schema type mismatch during migration.", "Table schema changes not replicated before data sync"),
            ("RDS multi-AZ failover delay", "Database failover took 5 minutes instead of seconds.", "Stale DNS cache in application client connection pool"),
            ("Database replica connection leak", "Standby nodes ran out of client connections, rejecting read traffic.", "Connection pool did not separate read and write pools correctly"),
            ("WAL directory out of space", "Write operations blocked on primary due to local disk full.", "Archiving script failed to copy WAL files to storage bucket"),
        ],
    },
    {
        "service": "CI Runner",
        "tags": ["github-actions", "runner", "security"],
        "variants": [
            ("Self-hosted runner compromise", "Privileged access key leaked from shared runner environment.", "Runner was configured as non-ephemeral across multiple PRs"),
            ("Docker-in-Docker security leak", "Shared host directory mounted in Docker-in-Docker runner context.", "Insecure dind setup in runner helm values"),
            ("CI runner cache poisoning", "Malicious dependency injected into shared node_modules cache.", "Write access allowed to caches on pull request runs"),
            ("Runner host memory exhaustion", "CI builds failed with runner lost communication error.", "Unbounded parallel build threads on single runner VM"),
            ("Runner registration token expiry", "Autoscaler could not register new GHA runners.", "Runner registration token expired in secrets manager"),
            ("Orphaned CI runner processes", "Build agent CPU saturated due to unkilled test processes.", "Timeout handlers missing in runner shell script"),
            ("Runner network isolation bypass", "Runner accessed private admin subnet resources.", "Missing VPC security groups boundaries on runner subnet"),
            ("Unverified action execution", "Build ran custom GitHub action from forks without approval.", "Repository workflow permissions allowed external actions"),
        ],
    },
    {
        "service": "Cloud Provider",
        "tags": ["cloud", "api", "outage"],
        "variants": [
            ("Cloud provider API rate limit throttling", "Terraform and deployment scripts failed to apply.", "Too many concurrent API calls from CI pipelines"),
            ("GCP Service Account deletion", "Applications lost access to GCP resources.", "Deployment script deleted active service account during cleanup"),
            ("AWS KMS key disabled", "Data decryption failed in production API.", "KMS key rotation script disabled the active key alias"),
            ("Cloud resource quota limit reached", "Unable to create new VM instances during peak traffic scaling.", "EC2 instance type limits reached in the availability zone"),
            ("AWS STS assume role timeout", "Kubernetes pods failed to acquire cloud credentials.", "IAM OIDC provider configuration mismatch or thumbprint expired"),
            ("GCP project quota exhaustion", "Build system failed to provision new test environments.", "Shared GCP billing account limits hit"),
            ("AWS billing lock on resources", "Cloud account suspended, shutting down all production workloads.", "Failed auto-payment due to expired credit card on account file"),
            ("KMS key policy lock", "Terraform lock out of key administration permissions.", "Key policy did not grant access to the account administrator role"),
        ],
    },
    {
        "service": "Container Registry",
        "tags": ["docker", "registry", "security"],
        "variants": [
            ("Docker registry auth token expiry", "Kubernetes pods failed to pull images during scale-out.", "Cron job for renewing registry credentials failed to run"),
            ("Production image tag overwritten", "Unstable code deployed to production due to mutable tags.", "Image tagging policy allowed overwriting existing tags like 'latest'"),
            ("Registry storage quota exceeded", "Docker build pipeline failed to push new images.", "Registry cleanup and garbage collection script failed"),
            ("Public push vulnerability", "Internal docker registry exposed push access without authentication.", "Registry config file binding to 0.0.0.0 instead of localhost"),
            ("Registry HTTP 502 bad gateway", "Deployment stuck due to repository server down.", "Registry database connection pool exhaustion"),
            ("Base image tag deletion", "Builds failed because base image was deleted from external registry.", "Mutable dependency on external upstream docker hub images"),
            ("Registry TLS wildcard mismatch", "Pulling docker images failed with insecure connection errors.", "Registry ingress updated with a certificate missing the subdomain"),
            ("Malicious image tag injection", "Build system pulled a poisoned container image.", "Registry access control allowed pull-request pushes to public repository"),
        ],
    },
    {
        "service": "Compliance Audit",
        "tags": ["compliance", "audit", "security"],
        "variants": [
            ("AWS Config rule deletion", "Compliance monitoring disabled for security group updates.", "Automated terraform cleanup script deleted policy rules"),
            ("Missing IAM permissions boundary", "Developers created administrator-level roles without boundary policy.", "Permissions boundary enforcement missing in IAM config"),
            ("Security Hub alerts ignored", "Critical alerts regarding public databases ignored.", "No alert forwarding configured for High/Critical severity issues"),
            ("S3 public access block disabled", "Account-level public access block disabled, exposing storage.", "Manual compliance override in AWS console"),
            ("Audit logs parsing failure", "CloudTrail logs failed to ingest into SIEM system.", "Incorrect SQS queue policy on log delivery bucket"),
            ("VPC flow logs disabled", "Network compliance audit failed due to missing flow records.", "Terraform VPC module variable set to false"),
            ("CIS benchmark failure", "Audit flag raised for root account access keys active.", "Root access key not deleted after initial setup"),
            ("GCP organization policy bypass", "Subprojects created public IP instances despite org constraint.", "Policy inheritance disabled on newly created project folders"),
        ],
    },
    {
        "service": "Identity Provider",
        "tags": ["auth", "identity", "security"],
        "variants": [
            ("SAML assertion certificate expiry", "SSO login failed for all enterprise users.", "SAML signing certificate expired on Identity Provider"),
            ("LDAP connection pool exhaustion", "User authentication requests failed with gateway timeout.", "LDAP client library did not close connections after bind operations"),
            ("WebAuthn MFA signature failure", "Users locked out during two-factor verification step.", "Incorrect challenge payload verification on backend server"),
            ("Active Directory sync timeout", "New employees could not log into internal applications.", "Network route between cloud connector and on-premise AD blocked"),
            ("OAuth redirect URI wildcard match", "Open redirect vulnerability exposed authorization codes.", "Identity provider configuration allowed wildcard redirects"),
            ("Keycloak server crash loop", "Authentication services down for 45 minutes.", "Keycloak database connection limits reached due to user spikes"),
            ("Expired Okta API token", "User sync script failed to provision new system accounts.", "Okta authorization token not rotated before expiration"),
            ("CSRF validation bypass", "SSO callback endpoint was vulnerable to CSRF attacks.", "Missing state token verification in callback handler"),
        ],
    },
    {
        "service": "Message Queue",
        "tags": ["rabbitmq", "messaging", "outage"],
        "variants": [
            ("RabbitMQ queue memory block", "Publishers blocked because memory limit threshold was reached.", "Consumers hung and did not acknowledge messages"),
            ("RabbitMQ cluster partition split-brain", "Nodes isolated, causing message loss.", "Network latency exceeded pause-minority timeout setting"),
            ("RabbitMQ connection leak", "Server rejected new client connections.", "Applications created a new connection per message instead of using channels"),
            ("RabbitMQ disk space alarm", "Broker blocked all incoming messages.", "Log files filled local disk space on rabbitmq nodes"),
            ("RabbitMQ channel leak", "High CPU usage on rabbitmq nodes due to thousands of open channels.", "Missing channel close block in client code try-finally statement"),
            ("RabbitMQ mirror sync loop", "Slow queue consumption during nodes sync.", "Sync-queue-size set too large on high-volume persistent queues"),
            ("RabbitMQ certificate handshake failed", "Clients could not connect via TLS.", "Stale CA certificate on RabbitMQ server node trust store"),
            ("RabbitMQ queue definition conflict", "Consumer failed to start due to queue attribute mismatch.", "Conflicting arguments like x-max-priority in consumer definition"),
        ],
    },
    {
        "service": "Feature Flag",
        "tags": ["config", "feature-flag", "outage"],
        "variants": [
            ("Feature flag fallback failure", "Application crashed when feature flag service was unreachable.", "Missing default hardcoded fallback values in initialization config"),
            ("Feature flag payload schema drift", "Client app crashed parsing invalid JSON from feature flag payload.", "Type mismatch between backend schema definition and client parser"),
            ("Feature flag configuration lock", "Unable to toggle off broken feature due to concurrent locks.", "Feature flag database backend locked during simultaneous updates"),
            ("Stale feature flag clean up error", "Clean up script removed active code path.", "Stale flag identified incorrectly in repository parse regex"),
            ("Feature flag evaluation latency", "API request latency doubled during checkout.", "Network round-trips for every local flag evaluation instead of caching"),
            ("Unsecured admin flag endpoint", "Attackers enabled premium features on regular accounts.", "Missing authentication guard on flag override REST endpoint"),
            ("Flag target group overlap", "Users received conflicting feature variations.", "Incorrect rule weight calculation in multivariate flag logic"),
            ("Feature flag cache invalidation lag", "Traffic continued to hit broken endpoint for 20 minutes.", "Long TTL set on client-side feature cache"),
        ],
    },
    {
        "service": "Static Hosting",
        "tags": ["s3", "cloudfront", "outage"],
        "variants": [
            ("CloudFront origin shield timeout", "Static files returned 504 Gateway Timeout.", "Origin shield region experiencing high latency or server failure"),
            ("Stale cache headers", "Users received outdated frontend javascript bundles after deployment.", "Cache-Control headers set to max-age=31536000 on index.html"),
            ("CloudFront index file missing", "Website root returned 403 Forbidden.", "Default root object not configured in CloudFront distribution"),
            ("S3 website origin bucket policy block", "Static hosting failed with access denied.", "Bucket policy changed, removing read access for CloudFront OAI"),
            ("CloudFront custom SSL certificate missing", "HTTPS connections to custom domain failed.", "ACM certificate deleted or not renewed before expiration"),
            ("CloudFront invalidation quota limit", "Frontend updates not visible due to invalidation queue block.", "Deployment script created wildcard invalidations for every single commit"),
            ("CloudFront geo-blocking misconfiguration", "Legitimate users blocked from accessing application.", "Incorrect ISO country codes added to restriction list"),
            ("CloudFront behavior routing error", "Dynamic API requests routed to static asset S3 bucket.", "Path pattern wildcard priority mismatch in distribution behaviors"),
        ],
    },
    {
        "service": "Ingress Controller",
        "tags": ["kubernetes", "ingress", "network"],
        "variants": [
            ("Ingress Nginx config reload failure", "Ingress controller stopped applying updates, returning 502.", "Invalid lua script configuration syntax injected via ingress annotation"),
            ("Ingress memory exhaustion", "Nginx ingress controller pod restarted continuously.", "Regex path pattern caused high CPU and memory growth under heavy load"),
            ("Ingress header size limit", "Users with large cookies received 400 Bad Request.", "Missing large-client-header-buffers tuning on ingress controller configmap"),
            ("Ingress SSL certificate mismatch", "Users received security warnings because default backend certificate was served.", "Ingress spec lacked the matching TLS host secret name configuration"),
            ("Ingress controller port exhaustion", "Ingress pods stopped accepting new connections.", "Incomplete connection closing by node upstream backend client"),
            ("Ingress rate limiting lockout", "Internal service communications blocked by ingress rate limiter.", "Incorrect client IP whitelist in rate limit annotation"),
            ("Ingress proxy buffer overflow", "Large responses from backend API returned 502 Bad Gateway.", "Proxy buffer size set too small for response payloads"),
            ("Ingress namespace watch crash", "Ingress controller stopped routing to new services.", "RBAC role missing list/watch permissions on namespaces"),
        ],
    },
    {
        "service": "Job Scheduler",
        "tags": ["cron", "kubernetes", "outage"],
        "variants": [
            ("CronJob concurrency policy blocker", "Critical daily processing job did not run.", "ConcurrencyPolicy set to Forbid and previous run hung silently"),
            ("Cron schedule syntax error", "Report generator job failed to start.", "Invalid cron expression parsed by scheduler service"),
            ("Batch script deadlock", "Data sync job took 24 hours instead of 5 minutes.", "Missing lock timeout on file write operation"),
            ("CronJob pod eviction", "Scheduled job aborted midway through execution.", "No resources request limits defined, causing node eviction under load"),
            ("Duplicate cron job executions", "Batch email campaign sent twice to users.", "Cronjob controller spawned duplicate pods due to transient API server delay"),
            ("Cron job timezone mismatch", "Database maintenance ran during peak traffic hours.", "Host timezone offset mismatch on kubernetes node group"),
            ("Cron task database connection leak", "Database crashed due to connection limit reached.", "Cron script did not release pool connections on completion"),
            ("Missing cron execution monitoring", "Silent failure of monthly data purge job went unnoticed.", "No warning triggers set on Failed or Dead state of cronjob pods"),
        ],
    },
    {
        "service": "Infrastructure Provisioning",
        "tags": ["terraform", "gcp", "outage"],
        "variants": [
            ("GCP provider auth failure", "Terraform apply failed to authenticate with Google Cloud API.", "Expired service account credentials key file"),
            ("GCP firewall rule deletion", "Production database isolated after automatic firewall rule cleanup.", "Incorrect priority index parameter in firewall configuration"),
            ("GCP IAM role binding conflict", "Access lost for support team after IAM role binding overwrite.", "Using google_project_iam_binding instead of google_project_iam_member"),
            ("GCP subnet allocation mismatch", "GKE cluster creation failed due to overlapping subnets.", "CIDR allocation block conflict in VPC configuration"),
            ("GCP disk resize failure", "Storage expansion failed because size decrease is unsupported.", "Reducing disk size in Terraform variable configuration"),
            ("GCP load balancer routing mismatch", "Traffic dropped on backend service after health check change.", "Unhealthy threshold value set too low"),
            ("GCP KMS key mismatch", "Cloud SQL database creation failed due to key availability issue.", "KMS key in a different region than the database instance"),
            ("GCP compute engine startup script crash", "New VMs failed to join cluster because bootstrap scripts failed.", "Missing dependency repository endpoint in boot template"),
        ],
    },
    {
        "service": "Data Pipeline",
        "tags": ["spark", "data", "processing"],
        "variants": [
            ("Spark job out of memory", "Daily analytics processing failed due to heap exhaustion.", "Incorrect driver/executor memory allocation settings"),
            ("Data pipeline file lock contention", "Batch process failed to write output parquet files.", "Overlapping job runs executing on the same partition path"),
            ("Data schema mismatch validation", "Spark streaming job crashed processing incoming event messages.", "Schema registry updated without backward compatibility check"),
            ("Databricks cluster scaling timeout", "Data pipeline jobs failed to start under high load.", "Cloud instance availability limits hit for requested node types"),
            ("BigQuery partition query limit", "Queries blocked due to partition scan limits exceeded.", "Missing partition filter constraint in client database queries"),
            ("Data pipeline timezone shift", "Aggregated stats reported incorrect daily summaries.", "Missing UTC conversion in ingestion pipeline transformer"),
            ("S3 bucket access denied in Spark", "Analytics job could not read input datasets.", "IAM role mismatch in Spark Hadoop cluster configuration"),
            ("Airflow DAG scheduler deadlock", "Data pipeline jobs did not trigger at scheduled intervals.", "Database connection pool exhaustion in Airflow scheduler"),
        ],
    },
    {
        "service": "Security Scanning",
        "tags": ["security-scanning", "compliance", "snyk"],
        "variants": [
            ("Snyk vulnerability build block", "CI pipeline aborted because critical security issue was detected.", "Automated block rule applied to transitive library dependency"),
            ("SonarQube quality gate failure", "Production release blocked by static analysis code quality check.", "New code coverage fell below the required 80% threshold"),
            ("Trivy image scan timeout", "Docker build pipeline failed during final vulnerability scan.", "Timeout waiting for Trivy database updates from registry server"),
            ("Secret leak scanner false positive", "Git commit rejected due to suspected private key match.", "Test mock certificates matching entropy pattern of real certificates"),
            ("OWASP Dependency Check crash", "Build failed to generate compliance reports.", "NVD database mirror unavailable during pipeline execution"),
            ("Docker image scanning bypass", "Vulnerable image promoted to production without security checks.", "Pipeline logic allowed skip-scan flag under emergency tags"),
            ("Terraform checkov analysis block", "IaC deployment aborted due to security validation warning.", "Missing public access block annotation on testing S3 bucket"),
            ("SAST scanner memory exhaustion", "Static analysis job killed by CI runner kernel.", "Huge monorepo codebase causing parser engine memory leaks"),
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
