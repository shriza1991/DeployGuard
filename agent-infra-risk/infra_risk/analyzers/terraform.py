"""
infra_risk.analyzers.terraform
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Deterministic security detectors for Terraform (*.tf, *.tfvars) files in a PR diff.

Rules
-----
TF_PUBLIC_S3            – public-read/public-read-write ACL or block_public_acls = false
TF_WILDCARD_IAM         – Action = "*" or Resource = "*"
TF_OPEN_INGRESS         – cidr_blocks = ["0.0.0.0/0"] (unrestricted ingress)
TF_PUBLIC_DB            – publicly_accessible = true
TF_DISABLED_ENCRYPTION  – encrypted = false or kms_key_id left empty
TF_MISSING_VERSION_PIN  – provider block without version constraint
"""
from __future__ import annotations

from .base import RichRule, TextAnalyzer, rich_rule


class TerraformAnalyzer(TextAnalyzer):
    name = "terraform"

    rich_rules: tuple[RichRule, ...] = (

        # ── TF_PUBLIC_S3 ──────────────────────────────────────────────────────
        rich_rule(
            pattern=(
                r"(?m)acl\s*=\s*[\"']public-(?:read|read-write)[\"']"
                r"|block_public_acls\s*=\s*false"
                r"|block_public_policy\s*=\s*false"
                r"|ignore_public_acls\s*=\s*false"
                r"|restrict_public_buckets\s*=\s*false"
            ),
            severity="CRITICAL",
            rule_id="TF_PUBLIC_S3",
            category="terraform",
            subcategory="public_storage",
            policy_action="BLOCK",
            confidence=0.98,
            reason=(
                "Terraform configures an S3 bucket with a public ACL or disables public-access block settings, "
                "exposing bucket contents to the internet."
            ),
            recommendation=(
                "Remove the public ACL and enforce the full public-access block:\n"
                "resource \"aws_s3_bucket_public_access_block\" \"example\" {\n"
                "  bucket                  = aws_s3_bucket.example.id\n"
                "  block_public_acls       = true\n"
                "  block_public_policy     = true\n"
                "  ignore_public_acls      = true\n"
                "  restrict_public_buckets = true\n"
                "}\n"
                "For intentionally public buckets (CDN, static site), use CloudFront with OAC instead."
            ),
            what_changed=(
                "The diff sets an S3 bucket ACL to 'public-read' or 'public-read-write', "
                "or disables one of the four aws_s3_bucket_public_access_block flags."
            ),
            why_dangerous=(
                "Public S3 buckets are a leading cause of cloud data breaches. "
                "Once public, the bucket contents can be enumerated and downloaded by anyone on the internet. "
                "Sensitive files (credentials, PII, backups, source code) are routinely exfiltrated "
                "from accidentally public buckets within hours of exposure (automated scanners watch for them)."
            ),
            attack_path=(
                "1. Terraform apply makes the bucket publicly readable/listable. "
                "2. Automated scanners (GrayhatWarfare, Shodan, trickest/inventory) discover the bucket within hours. "
                "3. Attacker downloads all objects, finds credentials/PII/code. "
                "4. If public-read-write: attacker uploads malware to serve from the bucket (phishing, typosquatting)."
            ),
            blast_radius=(
                "All objects in the bucket are world-readable/writable. "
                "Depending on contents: customer PII (GDPR/CCPA exposure), credentials for other services, "
                "application secrets, database backups. "
                "If used for static hosting: content injection affecting end users."
            ),
        ),

        # ── TF_WILDCARD_IAM ───────────────────────────────────────────────────
        rich_rule(
            pattern=(
                r"(?m)(?:\"Action\"\s*:\s*\[?\s*\"[*]\"\s*\]?"
                r"|action\s*=\s*[\"'][*][\"']"
                r"|\"Resource\"\s*:\s*\[?\s*\"[*]\"\s*\]?"
                r"|resource\s*=\s*[\"'][*][\"']"
                r"|AdministratorAccess)"
            ),
            severity="HIGH",
            rule_id="TF_WILDCARD_IAM",
            category="iam",
            subcategory="wildcard_permissions",
            policy_action="REVIEW_REQUIRED",
            confidence=0.95,
            reason=(
                "Terraform IAM policy grants wildcard actions (Action: *), "
                "wildcard resource access (Resource: *), or attaches AdministratorAccess."
            ),
            recommendation=(
                "Scope IAM permissions to only what the workload requires (least privilege):\n"
                "- Replace 'Action: *' with specific actions: [\"s3:GetObject\", \"s3:PutObject\"]\n"
                "- Replace 'Resource: *' with exact ARNs: \"arn:aws:s3:::my-bucket/*\"\n"
                "- Use IAM Access Analyzer to generate least-privilege policies from CloudTrail."
            ),
            what_changed=(
                "The diff adds or modifies an IAM policy document that grants 'Action: *', "
                "'Resource: *', or attaches the AWS-managed AdministratorAccess policy."
            ),
            why_dangerous=(
                "Wildcard IAM permissions grant the identity access to all AWS API actions "
                "across all resources in the account. "
                "A compromised service running under this role can exfiltrate all S3 data, "
                "create and manage EC2 instances, delete RDS databases, "
                "exfiltrate secrets from Secrets Manager, and perform privilege escalation "
                "to create new IAM users with console access."
            ),
            attack_path=(
                "1. Attacker achieves code execution inside the application (SSRF, RCE). "
                "2. They query the EC2 metadata service (169.254.169.254) to retrieve the instance role credentials. "
                "3. With Action:*/Resource:*, they call iam:CreateUser, iam:AttachUserPolicy "
                "   to create a persistent backdoor account. "
                "4. Full account takeover — all services, all regions."
            ),
            blast_radius=(
                "Full AWS account compromise if the role is assumed. "
                "All regions, all services, all data. "
                "Attacker can disable CloudTrail and GuardDuty to cover tracks."
            ),
        ),

        # ── TF_OPEN_INGRESS ───────────────────────────────────────────────────
        rich_rule(
            pattern=r"(?m)cidr_blocks\s*=\s*\[?\s*[\"']0\.0\.0\.0/0[\"']\s*\]?",
            severity="CRITICAL",
            rule_id="TF_OPEN_INGRESS",
            category="networking",
            subcategory="open_ingress",
            policy_action="BLOCK",
            confidence=0.98,
            reason=(
                "Terraform security group allows inbound traffic from 0.0.0.0/0 (all IPv4 addresses), "
                "exposing the resource to the public internet."
            ),
            recommendation=(
                "Restrict ingress CIDR to known IP ranges:\n"
                "ingress {\n"
                "  from_port   = 22\n"
                "  to_port     = 22\n"
                "  protocol    = \"tcp\"\n"
                "  cidr_blocks = [\"10.0.0.0/8\"]  # internal VPC only\n"
                "}\n"
                "For public-facing ports (80/443), use an Application Load Balancer with WAF "
                "in front of private instances rather than direct internet access."
            ),
            what_changed=(
                "The diff adds or modifies a security group ingress rule with cidr_blocks = [\"0.0.0.0/0\"], "
                "opening the resource to inbound connections from any IP address on the internet."
            ),
            why_dangerous=(
                "0.0.0.0/0 ingress rules place the resource directly on the public internet. "
                "SSH (22), RDP (3389), and database ports (3306, 5432) exposed this way are "
                "actively scanned and brute-forced within minutes of becoming reachable. "
                "Even if the service is authenticated, it is exposed to all known vulnerability scanners "
                "and zero-day exploits without any network-layer barrier."
            ),
            attack_path=(
                "1. Security group applies (terraform apply) — port becomes internet-reachable. "
                "2. Shodan/Censys index the open port within 15 minutes. "
                "3. Automated scanners attempt credential brute-force or exploit known CVEs. "
                "4. Successful exploit gives attacker a foothold inside the private VPC."
            ),
            blast_radius=(
                "The exposed instance is at direct internet risk. "
                "If compromised: full VPC network access (no VPN or bastion required). "
                "Lateral movement to RDS, ElastiCache, internal APIs via VPC private routing."
            ),
        ),

        # ── TF_PUBLIC_DB ─────────────────────────────────────────────────────
        rich_rule(
            pattern=r"(?m)publicly_accessible\s*=\s*true\b",
            severity="CRITICAL",
            rule_id="TF_PUBLIC_DB",
            category="terraform",
            subcategory="public_database",
            policy_action="BLOCK",
            confidence=0.98,
            reason=(
                "Terraform RDS/Aurora/Redshift instance is configured with publicly_accessible = true, "
                "making the database endpoint reachable from the public internet."
            ),
            recommendation=(
                "Set publicly_accessible = false and place the database in private VPC subnets:\n"
                "resource \"aws_db_instance\" \"example\" {\n"
                "  publicly_accessible = false\n"
                "  db_subnet_group_name = aws_db_subnet_group.private.name\n"
                "}\n"
                "Applications should connect via private VPC routing, not the public endpoint."
            ),
            what_changed=(
                "The diff sets 'publicly_accessible = true' on a database resource, "
                "assigning it a public endpoint and allowing connections from outside the VPC."
            ),
            why_dangerous=(
                "A publicly accessible database endpoint is reachable by any host on the internet. "
                "Database authentication is the only barrier — no network-layer protection. "
                "Known CVEs in database engines, misconfigured authentication, "
                "or credential leakage all become directly exploitable without VPN or bastion access."
            ),
            attack_path=(
                "1. Database is assigned a public DNS endpoint after terraform apply. "
                "2. Endpoint is discovered via DNS enumeration or port scanning. "
                "3. Attacker brute-forces credentials or exploits a known CVE in the DB engine. "
                "4. Full database access: data exfiltration, credential harvest, ransomware."
            ),
            blast_radius=(
                "All data in the database is at risk. "
                "If the DB stores customer PII: GDPR/CCPA breach notification obligations. "
                "If the DB stores application secrets: full application compromise possible."
            ),
        ),

        # ── TF_DISABLED_ENCRYPTION ────────────────────────────────────────────
        rich_rule(
            pattern=(
                r"(?m)encrypted\s*=\s*false\b"
                r"|storage_encrypted\s*=\s*false\b"
                r"|enable_encryption\s*=\s*false\b"
            ),
            severity="HIGH",
            rule_id="TF_DISABLED_ENCRYPTION",
            category="terraform",
            subcategory="encryption",
            policy_action="REVIEW_REQUIRED",
            confidence=0.95,
            reason=(
                "Terraform resource explicitly disables encryption at rest "
                "(encrypted = false / storage_encrypted = false)."
            ),
            recommendation=(
                "Enable encryption at rest:\n"
                "- For EBS: encrypted = true, kms_key_id = aws_kms_key.example.arn\n"
                "- For RDS: storage_encrypted = true, kms_key_id = aws_kms_key.example.arn\n"
                "- For S3: use aws_s3_bucket_server_side_encryption_configuration\n"
                "Use customer-managed KMS keys (CMK) for regulated data to maintain key control."
            ),
            what_changed=(
                "The diff explicitly sets 'encrypted = false' or 'storage_encrypted = false' "
                "on an EBS volume, RDS instance, or similar storage resource, "
                "disabling encryption at rest."
            ),
            why_dangerous=(
                "Unencrypted storage means that if the underlying physical media or snapshot "
                "is accessed by an unauthorized party (AWS account compromise, insider threat, "
                "cloud provider breach), the data is readable without any key material. "
                "Most compliance frameworks (PCI-DSS, HIPAA, SOC2) require encryption at rest."
            ),
            attack_path=(
                "1. EBS snapshot or RDS snapshot is accidentally shared or made public. "
                "2. Attacker mounts the unencrypted snapshot in their own AWS account. "
                "3. Full data access — no encryption key required. "
                "4. Customer PII, credentials, and business data exfiltrated."
            ),
            blast_radius=(
                "All data stored on the resource is at risk of exposure via snapshot access. "
                "Compliance violations: GDPR, HIPAA, PCI-DSS penalties. "
                "Breach notification obligations if PII is stored."
            ),
        ),

        # ── TF_MISSING_VERSION_PIN ────────────────────────────────────────────
        rich_rule(
            pattern=(
                r"(?m)^\+?\s*source\s*=\s*[\"'](?:hashicorp|registry\.terraform\.io)/[^\"']+[\"']\s*\n"
                r"(?!\s*version)"
            ),
            severity="MEDIUM",
            rule_id="TF_MISSING_VERSION_PIN",
            category="terraform",
            subcategory="unpinned_version",
            policy_action="REVIEW_REQUIRED",
            confidence=0.82,
            reason=(
                "Terraform provider or module block does not specify a version constraint, "
                "allowing future terraform init to download an incompatible or compromised version."
            ),
            recommendation=(
                "Always pin provider and module versions:\n"
                "terraform {\n"
                "  required_providers {\n"
                "    aws = {\n"
                "      source  = \"hashicorp/aws\"\n"
                "      version = \"~> 5.50\"\n"
                "    }\n"
                "  }\n"
                "}\n"
                "Lock with 'terraform init -lockfile=readonly' and commit the .terraform.lock.hcl file."
            ),
            what_changed=(
                "The diff adds a provider or module source without a corresponding version constraint, "
                "meaning 'terraform init' will download the latest available version."
            ),
            why_dangerous=(
                "Without version pinning, any 'terraform init' or CI pipeline run can pull a "
                "newer provider version that introduces breaking changes or, in a supply-chain attack scenario, "
                "a compromised provider release. "
                "Terraform's public registry has been targeted in supply-chain attacks (typosquatting)."
            ),
            attack_path=(
                "1. Attacker publishes a compromised patch version of the provider to the Terraform registry. "
                "2. Unpinned terraform init pulls the malicious version. "
                "3. Provider executes attacker code during plan/apply with cloud credentials. "
                "4. Cloud account credentials exfiltrated."
            ),
            blast_radius=(
                "Any terraform apply using the compromised provider version is affected. "
                "Cloud credentials used during apply are at risk. "
                "Infrastructure state may be corrupted or backdoored."
            ),
        ),
    )
