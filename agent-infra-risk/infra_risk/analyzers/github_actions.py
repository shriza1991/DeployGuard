"""
infra_risk.analyzers.github_actions
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Deterministic security detectors for GitHub Actions workflow files in a PR diff.

Rules
-----
GHA_WRITE_ALL_PERMISSIONS    – permissions: write-all or permissions: { contents: write } top-level
GHA_SECRETS_ECHO             – echo ${{ secrets.* }} or similar secret leakage
GHA_UNPINNED_ACTION          – uses: owner/action@branch (not @sha)
GHA_PULL_REQUEST_TARGET      – pull_request_target trigger (supply-chain risk)
GHA_ARBITRARY_SHELL          – curl | bash / wget | sh patterns
"""
from __future__ import annotations

import re
from .base import Finding, RichRule, TextAnalyzer, rich_rule, SEVERITY_WEIGHTS


class GitHubActionsAnalyzer(TextAnalyzer):
    name = "github_actions"

    rich_rules: tuple[RichRule, ...] = (

        # ── GHA_WRITE_ALL_PERMISSIONS ─────────────────────────────────────────
        rich_rule(
            pattern=r"(?m)^\+?\s*permissions\s*:\s*write-all\b",
            severity="CRITICAL",
            rule_id="GHA_WRITE_ALL_PERMISSIONS",
            category="github_actions",
            subcategory="permissions",
            policy_action="BLOCK",
            confidence=0.98,
            reason=(
                "GitHub Actions workflow grants write-all permissions, "
                "giving the workflow token write access to the entire repository scope."
            ),
            recommendation=(
                "Replace 'permissions: write-all' with scoped, minimal permissions:\n"
                "permissions:\n"
                "  contents: read\n"
                "  pull-requests: write\n"
                "Grant only what each job strictly requires."
            ),
            what_changed=(
                "The diff sets 'permissions: write-all' at the workflow or job level, "
                "elevating the GITHUB_TOKEN to full write access across all repository scopes."
            ),
            why_dangerous=(
                "The GITHUB_TOKEN with write-all can push commits, create releases, "
                "modify branch protection rules, approve pull requests, and manage repository settings. "
                "If the workflow is triggered on untrusted input (e.g. PR from a fork), "
                "a malicious workflow step could weaponize this token to tamper with the repository."
            ),
            attack_path=(
                "1. Workflow is triggered by a PR from a fork (or pull_request_target). "
                "2. Attacker's workflow step exfiltrates GITHUB_TOKEN via curl to attacker server. "
                "3. Attacker uses the token to push a backdoored commit, modify CODEOWNERS, "
                "   or approve their own PR, bypassing code review."
            ),
            blast_radius=(
                "Repository integrity: unauthorized commits, branch protection bypass. "
                "Supply-chain: if this repo is a library, downstream consumers are affected. "
                "Secret leakage: workflows with write-all can read Actions secrets via modified workflow files."
            ),
        ),

        # ── GHA_SECRETS_ECHO ─────────────────────────────────────────────────
        rich_rule(
            pattern=r"(?m)echo\s+['\"]?\$\{\{\s*secrets\.[A-Za-z0-9_]+\s*\}\}",
            severity="CRITICAL",
            rule_id="GHA_SECRETS_ECHO",
            category="github_actions",
            subcategory="secret_leakage",
            policy_action="BLOCK",
            confidence=0.97,
            reason=(
                "A GitHub Actions step echoes a secret value to stdout. "
                "This exposes the secret in workflow logs, which may be accessible to all repository contributors."
            ),
            recommendation=(
                "Never echo secrets directly. "
                "GitHub automatically masks registered secrets in logs, but this masking is bypassed "
                "by encoding tricks. "
                "Pass secrets to tools via stdin, environment variables, or files with restricted permissions. "
                "Remove the echo step entirely."
            ),
            what_changed=(
                "The diff introduces an 'echo ${{ secrets.<NAME> }}' or equivalent expression "
                "inside a workflow run step, printing a secret to the workflow log stream."
            ),
            why_dangerous=(
                "Workflow logs are stored by GitHub and accessible to all repository collaborators with "
                "'Actions: read' permission. "
                "Even though GitHub attempts to mask known secrets, the masking can be defeated with "
                "simple string transformations (base64, splitting across multiple echo calls). "
                "A leaked secret cannot be un-leaked from existing log archives."
            ),
            attack_path=(
                "1. Workflow runs on a PR, push, or schedule. "
                "2. Secret value appears in the public or internal Actions log. "
                "3. Any collaborator (or public viewer on a public repo) captures the secret. "
                "4. Credential is used to access external APIs, databases, or cloud accounts."
            ),
            blast_radius=(
                "Any service authenticated by the exposed secret is at risk. "
                "Impact scope depends on the secret: could be a cloud account, "
                "production database, payment processor, or internal API. "
                "On public repositories, the log is world-readable."
            ),
        ),

        # ── GHA_UNPINNED_ACTION ───────────────────────────────────────────────
        rich_rule(
            pattern=r"(?m)^\+?\s*uses\s*:\s*[A-Za-z0-9_\-]+/[A-Za-z0-9_\-]+@(?:main|master|latest|v\d+)\b",
            severity="HIGH",
            rule_id="GHA_UNPINNED_ACTION",
            category="github_actions",
            subcategory="supply_chain",
            policy_action="REVIEW_REQUIRED",
            confidence=0.95,
            reason=(
                "GitHub Actions workflow uses an action pinned to a mutable ref (branch name or version tag) "
                "instead of an immutable commit SHA."
            ),
            recommendation=(
                "Pin actions to a full 40-character commit SHA:\n"
                "  uses: actions/checkout@b4ffde65f46336ab88eb53be808477a3936bae11  # v4.1.1\n"
                "Use Dependabot or 'pin-github-action' CLI to automate SHA pinning."
            ),
            what_changed=(
                "The diff references a GitHub Action using a branch name (main/master), "
                "a floating version tag (v1, latest), or similar mutable reference."
            ),
            why_dangerous=(
                "Branch names and version tags are mutable pointers. "
                "The action author (or an attacker who compromises their account) can push new code "
                "to the tag without any change to the workflow file. "
                "The next workflow run silently executes the new, potentially malicious code "
                "with full access to repository secrets and the GITHUB_TOKEN."
            ),
            attack_path=(
                "1. Attacker compromises the action maintainer's GitHub account (credential stuffing, phishing). "
                "2. They push malicious code to the 'main' branch or overwrite the 'v1' tag. "
                "3. All workflows using 'owner/action@main' silently execute the malicious code. "
                "4. Attacker extracts all secrets, GITHUB_TOKEN, and repository content."
            ),
            blast_radius=(
                "Every repository using this action is affected simultaneously. "
                "Secrets from all consumers are at risk. "
                "This is a classic supply-chain attack (similar to the tj-actions/changed-files incident)."
            ),
        ),

        # ── GHA_PULL_REQUEST_TARGET ───────────────────────────────────────────
        rich_rule(
            pattern=r"(?m)^\+?\s*on\s*:.*pull_request_target|^\+?\s*pull_request_target\s*:",
            severity="HIGH",
            rule_id="GHA_PULL_REQUEST_TARGET",
            category="github_actions",
            subcategory="trigger_misuse",
            policy_action="REVIEW_REQUIRED",
            confidence=0.92,
            reason=(
                "Workflow uses the 'pull_request_target' trigger, which runs in the context of the "
                "base repository with access to secrets — even when triggered by a fork PR."
            ),
            recommendation=(
                "If 'pull_request_target' is required (e.g. for PR labeling), "
                "never check out or execute code from the PR head in the same job:\n"
                "- Do NOT use: actions/checkout with ref: ${{ github.event.pull_request.head.sha }}\n"
                "- Split into a separate job gated by an environment approval.\n"
                "Prefer 'pull_request' trigger for workflows that run contributed code."
            ),
            what_changed=(
                "The diff introduces or modifies a 'pull_request_target' trigger on a workflow "
                "that may also check out or run code from the PR's head branch."
            ),
            why_dangerous=(
                "'pull_request_target' runs in the security context of the base repository, "
                "meaning it has access to repository secrets — unlike the safer 'pull_request' trigger. "
                "If the workflow also checks out the PR head code and executes it, "
                "a malicious contributor can craft a PR that executes arbitrary code "
                "with access to all repository secrets."
            ),
            attack_path=(
                "1. Attacker opens a PR from a fork modifying a Makefile, script, or test fixture. "
                "2. Workflow uses pull_request_target and checks out the PR head. "
                "3. The attacker's code runs with repository secrets in the environment. "
                "4. Secrets are exfiltrated via curl/DNS exfiltration."
            ),
            blast_radius=(
                "All repository secrets accessible to the workflow are exposed. "
                "This includes deployment keys, cloud credentials, package registry tokens. "
                "This attack pattern has been used in real-world supply-chain attacks on OSS projects."
            ),
        ),

        # ── GHA_ARBITRARY_SHELL ───────────────────────────────────────────────
        rich_rule(
            pattern=r"(?m)(?:curl|wget)\s+\S+\s*\|[^|]*(?:bash|sh|python|ruby|perl)\b",
            severity="HIGH",
            rule_id="GHA_ARBITRARY_SHELL",
            category="github_actions",
            subcategory="remote_execution",
            policy_action="REVIEW_REQUIRED",
            confidence=0.95,
            reason=(
                "Workflow step pipes remote content directly into a shell interpreter "
                "(curl/wget | bash). This executes arbitrary remote code without integrity verification."
            ),
            recommendation=(
                "Download the script to a file, verify its SHA256 checksum, then execute:\n"
                "  run: |\n"
                "    curl -fsSL https://example.com/install.sh -o install.sh\n"
                "    echo '<expected-sha256>  install.sh' | sha256sum -c -\n"
                "    bash install.sh\n"
                "Or use an official GitHub Action for the tool instead."
            ),
            what_changed=(
                "The diff adds a 'run' step that pipes the output of curl or wget "
                "directly into bash or sh without any checksum verification."
            ),
            why_dangerous=(
                "The remote URL is fetched at runtime over HTTPS, but HTTPS only ensures transport security "
                "— not content integrity. "
                "A compromised CDN, DNS hijack, or server-side compromise can serve a different script. "
                "The script executes with full access to the runner's environment, "
                "including all secrets and the GITHUB_TOKEN."
            ),
            attack_path=(
                "1. Attacker compromises the script hosting server or performs a DNS hijack. "
                "2. Malicious script is served to the Actions runner. "
                "3. Script runs in the workflow environment with access to all secrets. "
                "4. Secrets exfiltrated, repository contents read, artifacts tampered."
            ),
            blast_radius=(
                "All secrets and environment variables available to the workflow step are at risk. "
                "The runner filesystem and any mounted service accounts are accessible. "
                "Attacker can push tampered build artifacts to the deployment pipeline."
            ),
        ),
    )
