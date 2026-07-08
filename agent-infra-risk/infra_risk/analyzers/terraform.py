from __future__ import annotations

from .base import TextAnalyzer, rule


class TerraformAnalyzer(TextAnalyzer):
    name = "terraform"

    rules = (
        rule(r"\b0\.0\.0\.0/0\b", "critical", "Open security groups allow 0.0.0.0/0.", "Restrict CIDR ranges to trusted networks and avoid public ingress."),
        rule(r"\bpublic\s+s3\s+bucket\b|\bs3\b[^\n.]*\bpublic\b", "critical", "Terraform creates a public S3 bucket.", "Keep S3 buckets private by default and use explicit public access blocks."),
        rule(r"\bacl\s*=\s*[\"']?public-read[\"']?\b", "critical", "Terraform sets an S3 ACL to public-read.", "Use private ACLs and S3 public access block settings."),
        rule(r"\bpublic-read-write\b", "critical", "Terraform sets an S3 ACL to public-read-write.", "Never grant public write access to S3 buckets."),
        rule(r"\bpublicly_accessible\s*=\s*true\b", "critical", "Terraform enables public database accessibility.", "Keep databases private and expose them only through controlled network paths."),
        rule(r"\bterraform\s+destroy\b|\bdestroy\b", "high", "Terraform destroy behavior detected.", "Require explicit approval and safeguards for destructive infrastructure actions."),
        rule(r"\bforce_destroy\s*=\s*true\b", "high", "Terraform force_destroy is enabled.", "Disable force_destroy unless deletion of non-empty resources is explicitly approved."),
        rule(r"\baction\s*=\s*[\"']?\*[\"']?|\baction\s*=\s*\[\s*[\"']\*[\"']\s*\]", "critical", "Terraform IAM policy grants wildcard actions.", "Replace wildcard actions with the minimum required permissions."),
        rule(r"\bresource\s*=\s*[\"']?\*[\"']?|\bresource\s*=\s*\[\s*[\"']\*[\"']\s*\]", "critical", "Terraform IAM policy grants wildcard resources.", "Scope IAM resources to the exact ARNs required."),
        rule(r"\bkms\b[^\n.]*\bdisabled\b|\bkms\s*=\s*false\b", "high", "Terraform disables KMS encryption.", "Enable KMS-backed encryption for managed resources."),
        rule(r"\bencryption\s+disabled\b|\bencryption\s*=\s*false\b", "high", "Terraform disables encryption.", "Enable encryption at rest for infrastructure resources."),
        rule(r"\bskip_final_snapshot\s*=\s*true\b", "high", "Terraform skips the final database snapshot.", "Require a final snapshot before deleting stateful databases."),
    )
