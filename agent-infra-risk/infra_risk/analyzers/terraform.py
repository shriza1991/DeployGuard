from __future__ import annotations

from .base import TextAnalyzer, rule


class TerraformAnalyzer(TextAnalyzer):
    name = "terraform"

    rules = (
        rule(
            r"\b0\.0\.0\.0/0\b",
            severity="CRITICAL",
            reason="Open security group ingress rule permits 0.0.0.0/0 unrestricted public access.",
            recommendation="Restrict ingress CIDR ranges to trusted bastion IP addresses or internal subnets.",
            rule_id="TERRAFORM_OPEN_SSH",
            category="networking",
            subcategory="open_ingress",
            policy_action="BLOCK",
            confidence=0.98,
        ),
        rule(
            r"\bacl\s*=\s*[\"']?public-(?:read|read-write)[\"']?\b|\bpublic\s+s3\s+bucket\b|\bs3\b[^\n.]*\bpublic\b",
            severity="CRITICAL",
            reason="Terraform configures a public S3 bucket ACL (public-read / public-read-write).",
            recommendation="Keep S3 buckets private and configure explicit aws_s3_bucket_public_access_block.",
            rule_id="TERRAFORM_PUBLIC_S3",
            category="terraform",
            subcategory="public_storage",
            policy_action="BLOCK",
            confidence=0.98,
        ),
        rule(
            r"\baction\s*=\s*[\"']?\*[\"']?|\baction\s*=\s*\[\s*[\"']\*[\"']\s*\]|\badministratoraccess\b",
            severity="HIGH",
            reason="Terraform IAM policy grants wildcard actions (Action: *) or AdministratorAccess.",
            recommendation="Scope IAM actions to the specific minimal privileges required.",
            rule_id="TERRAFORM_WILDCARD_IAM",
            category="iam",
            subcategory="wildcard_permissions",
            policy_action="REVIEW_REQUIRED",
            confidence=0.95,
        ),
        rule(
            r"\bresource\s*=\s*[\"']?\*[\"']?|\bresource\s*=\s*\[\s*[\"']\*[\"']\s*\]",
            severity="HIGH",
            reason="Terraform IAM policy grants wildcard resource access (Resource: *).",
            recommendation="Scope IAM resource blocks to exact resource ARNs.",
            rule_id="TERRAFORM_WILDCARD_IAM",
            category="iam",
            subcategory="wildcard_permissions",
            policy_action="REVIEW_REQUIRED",
            confidence=0.95,
        ),
        rule(
            r"\bpublicly_accessible\s*=\s*true\b",
            severity="CRITICAL",
            reason="Database instance configured with publicly_accessible = true.",
            recommendation="Set publicly_accessible = false and deploy database in private VPC subnets.",
            rule_id="TERRAFORM_PUBLIC_DB",
            category="terraform",
            subcategory="public_database",
            policy_action="BLOCK",
            confidence=0.98,
        ),
        rule(
            r"\bforce_destroy\s*=\s*true\b",
            severity="HIGH",
            reason="Terraform resource has force_destroy = true enabled.",
            recommendation="Disable force_destroy on stateful resources to prevent accidental data deletion.",
            rule_id="TERRAFORM_FORCE_DESTROY",
            category="terraform",
            subcategory="data_loss",
            policy_action="REVIEW_REQUIRED",
            confidence=0.90,
        ),
    )

