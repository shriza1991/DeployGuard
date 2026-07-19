"""
DeployGuard Automated Regression Test Suite

Validates AI Risk Agents and Aggregator Policy Engine decision-making
against mandatory DevSecOps benchmark scenarios.
"""

import os
import sys
import pytest

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(ROOT_DIR, "agent-infra-risk"))
sys.path.insert(0, os.path.join(ROOT_DIR, "agent-code-risk"))
sys.path.insert(0, os.path.join(ROOT_DIR, "aggregator"))

import importlib.util

def _import_module_from_path(module_name: str, file_path: str):
    spec = importlib.util.spec_from_file_location(module_name, file_path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module

code_risk_mod = _import_module_from_path("code_risk_analyzers", os.path.join(ROOT_DIR, "agent-code-risk", "risk_analyzers.py"))
infra_risk_mod = _import_module_from_path("infra_risk_analyzers", os.path.join(ROOT_DIR, "agent-infra-risk", "risk_analyzers.py"))
decision_engine_mod = _import_module_from_path("decision_engine", os.path.join(ROOT_DIR, "aggregator", "decision_engine.py"))

code_risk_analyzer = code_risk_mod.analyze_code_risk
infra_risk_analyzer = infra_risk_mod.analyze_infra_risk
make_decision = decision_engine_mod.make_decision


def test_scenario_readme_only():
    """Scenario 1: README/docs-only change -> Expected: SAFE"""
    payload = {
        "repository": {"name": "myorg/docs-repo"},
        "pull_request": {
            "title": "docs: update deployment architecture diagram & instructions for Docker",
            "body": "Updated README.md with docker, container, and infrastructure documentation.",
            "changed_files": 1,
        },
        "changed_files": [
            {
                "filename": "README.md",
                "patch": "+ # DeployGuard Setup\n+ Update docker compose setup guide.\n+ Container security notes.",
            }
        ],
    }

    code_res = code_risk_analyzer(payload)
    infra_res = infra_risk_analyzer(payload)

    agent_results = {
        "code-risk": code_res,
        "infra-risk": infra_res,
        "incident-history": {"score": 10, "severity": "low", "confidence": 0.5},
    }

    decision = make_decision("test-readme-corr-id", agent_results)

    assert decision["decision"] == "SAFE", f"Expected SAFE for README only, got {decision['decision']}"
    assert decision["overall_score"] < 30, f"Expected low score, got {decision['overall_score']}"


def test_scenario_dependency_update():
    """Scenario 2: Dependency update -> Expected: SAFE"""
    payload = {
        "repository": {"name": "myorg/app"},
        "pull_request": {
            "title": "chore(deps): bump axios from 1.6.0 to 1.7.0",
            "body": "Bumps axios version in package.json.",
        },
        "changed_files": [
            {
                "filename": "package.json",
                "patch": '-    "axios": "^1.6.0"\n+    "axios": "^1.7.0"',
            }
        ],
    }

    code_res = code_risk_analyzer(payload)
    infra_res = infra_risk_analyzer(payload)

    agent_results = {
        "code-risk": code_res,
        "infra-risk": infra_res,
        "incident-history": {"score": 10, "severity": "low", "confidence": 0.5},
    }

    decision = make_decision("test-dep-corr-id", agent_results)

    assert decision["decision"] == "SAFE", f"Expected SAFE for dependency update, got {decision['decision']}"


def test_scenario_user_root():
    """Scenario 3: Dockerfile USER root -> Expected: REVIEW"""
    payload = {
        "repository": {"name": "myorg/api"},
        "pull_request": {
            "title": "fix: update dockerfile user permission context",
            "body": "Sets user to root inside dockerfile.",
        },
        "changed_files": [
            {
                "filename": "Dockerfile",
                "patch": "FROM python:3.11-slim\n+ USER root\nWORKDIR /app\nCMD [\"python\", \"app.py\"]",
            }
        ],
    }

    code_res = code_risk_analyzer(payload)
    infra_res = infra_risk_analyzer(payload)

    agent_results = {
        "code-risk": code_res,
        "infra-risk": infra_res,
        "incident-history": {"score": 10, "severity": "low", "confidence": 0.5},
    }

    decision = make_decision("test-user-root-corr-id", agent_results)

    assert decision["decision"] == "REVIEW", f"Expected REVIEW for USER root, got {decision['decision']}"
    assert any(f.get("rule_id") == "DOCKER_ROOT_USER" for f in decision["deterministic_findings"]), "DOCKER_ROOT_USER rule missing"


def test_scenario_user_root_plus_latest():
    """Scenario 4: USER root + FROM latest tag -> Expected: REVIEW (High score)"""
    payload = {
        "repository": {"name": "myorg/api"},
        "pull_request": {
            "title": "build: update base image to python:latest and run as root",
            "body": "Switches base image to latest python tag.",
        },
        "changed_files": [
            {
                "filename": "Dockerfile",
                "patch": "+ FROM python:latest\n+ USER root\nWORKDIR /app",
            }
        ],
    }

    code_res = code_risk_analyzer(payload)
    infra_res = infra_risk_analyzer(payload)

    agent_results = {
        "code-risk": code_res,
        "infra-risk": infra_res,
        "incident-history": {"score": 10, "severity": "low", "confidence": 0.5},
    }

    decision = make_decision("test-root-latest-corr-id", agent_results)

    assert decision["decision"] == "REVIEW", f"Expected REVIEW for USER root + latest, got {decision['decision']}"
    assert decision["overall_score"] >= 45, f"Expected higher score >= 45, got {decision['overall_score']}"


def test_scenario_privileged_kubernetes():
    """Scenario 5: Privileged Kubernetes pod -> Expected: BLOCK"""
    payload = {
        "repository": {"name": "myorg/k8s-manifests"},
        "pull_request": {
            "title": "feat: enable privileged securityContext on deployment",
            "body": "Enables privileged mode for container.",
        },
        "changed_files": [
            {
                "filename": "deployment.yaml",
                "patch": "containers:\n  - name: app\n    securityContext:\n+     privileged: true",
            }
        ],
    }

    code_res = code_risk_analyzer(payload)
    infra_res = infra_risk_analyzer(payload)

    agent_results = {
        "code-risk": code_res,
        "infra-risk": infra_res,
        "incident-history": {"score": 10, "severity": "low", "confidence": 0.5},
    }

    decision = make_decision("test-k8s-priv-corr-id", agent_results)

    assert decision["decision"] == "BLOCK", f"Expected BLOCK for privileged k8s pod, got {decision['decision']}"
    assert any(f.get("rule_id") == "K8S_PRIVILEGED_POD" for f in decision["deterministic_findings"]), "K8S_PRIVILEGED_POD rule missing"


def test_scenario_open_ssh_ingress():
    """Scenario 6: Open SSH (0.0.0.0/0) -> Expected: BLOCK"""
    payload = {
        "repository": {"name": "myorg/terraform"},
        "pull_request": {
            "title": "infra: allow SSH access from anywhere",
            "body": "Opens port 22 ingress.",
        },
        "changed_files": [
            {
                "filename": "main.tf",
                "patch": "ingress {\n  from_port = 22\n  to_port = 22\n+ cidr_blocks = [\"0.0.0.0/0\"]\n}",
            }
        ],
    }

    code_res = code_risk_analyzer(payload)
    infra_res = infra_risk_analyzer(payload)

    agent_results = {
        "code-risk": code_res,
        "infra-risk": infra_res,
        "incident-history": {"score": 10, "severity": "low", "confidence": 0.5},
    }

    decision = make_decision("test-ssh-corr-id", agent_results)

    assert decision["decision"] == "BLOCK", f"Expected BLOCK for 0.0.0.0/0 SSH, got {decision['decision']}"
    assert any(f.get("rule_id") == "TERRAFORM_OPEN_SSH" for f in decision["deterministic_findings"]), "TERRAFORM_OPEN_SSH rule missing"


def test_scenario_public_s3_bucket():
    """Scenario 7: Public S3 Bucket -> Expected: BLOCK"""
    payload = {
        "repository": {"name": "myorg/terraform"},
        "pull_request": {
            "title": "infra: add public s3 bucket for static assets",
            "body": "Sets S3 bucket acl to public-read.",
        },
        "changed_files": [
            {
                "filename": "s3.tf",
                "patch": "resource \"aws_s3_bucket\" \"b\" {\n  bucket = \"my-assets\"\n+ acl = \"public-read\"\n}",
            }
        ],
    }

    code_res = code_risk_analyzer(payload)
    infra_res = infra_risk_analyzer(payload)

    agent_results = {
        "code-risk": code_res,
        "infra-risk": infra_res,
        "incident-history": {"score": 10, "severity": "low", "confidence": 0.5},
    }

    decision = make_decision("test-s3-corr-id", agent_results)

    assert decision["decision"] == "BLOCK", f"Expected BLOCK for public S3 bucket, got {decision['decision']}"
    assert any(f.get("rule_id") == "TERRAFORM_PUBLIC_S3" for f in decision["deterministic_findings"]), "TERRAFORM_PUBLIC_S3 rule missing"


def test_scenario_aws_secret_key():
    """Scenario 8: Hardcoded AWS Secret -> Expected: BLOCK"""
    payload = {
        "repository": {"name": "myorg/backend"},
        "pull_request": {
            "title": "fix: add AWS credentials config",
            "body": "Hardcodes AWS secret key.",
        },
        "changed_files": [
            {
                "filename": "config.py",
                "patch": "+ AWS_ACCESS_KEY_ID = \"AKIAIOSFODNN7EXAMPLE\"\n+ AWS_SECRET_ACCESS_KEY = \"wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY\"",
            }
        ],
    }

    code_res = code_risk_analyzer(payload)
    infra_res = infra_risk_analyzer(payload)

    agent_results = {
        "code-risk": code_res,
        "infra-risk": infra_res,
        "incident-history": {"score": 10, "severity": "low", "confidence": 0.5},
    }

    decision = make_decision("test-secret-corr-id", agent_results)

    assert decision["decision"] == "BLOCK", f"Expected BLOCK for AWS secret, got {decision['decision']}"
    assert any(f.get("rule_id") == "HARDCODED_AWS_CREDENTIALS" for f in decision["deterministic_findings"]), "HARDCODED_AWS_CREDENTIALS rule missing"


def test_scenario_remove_auth_middleware():
    """Scenario 9: Remove authentication middleware -> Expected: REVIEW / BLOCK"""
    payload = {
        "repository": {"name": "myorg/api"},
        "pull_request": {
            "title": "refactor: simplify request pipeline",
            "body": "Removes auth middleware from router.",
        },
        "changed_files": [
            {
                "filename": "router.py",
                "patch": "- @app.middleware('http')\n- async def verify_auth_token(request, call_next):\n-     return check_session_guard(request)",
            }
        ],
    }

    code_res = code_risk_analyzer(payload)
    infra_res = infra_risk_analyzer(payload)

    agent_results = {
        "code-risk": code_res,
        "infra-risk": infra_res,
        "incident-history": {"score": 10, "severity": "low", "confidence": 0.5},
    }

    decision = make_decision("test-auth-remove-corr-id", agent_results)

    assert decision["decision"] in {"REVIEW", "BLOCK"}, f"Expected REVIEW or BLOCK for auth removal, got {decision['decision']}"
    assert any(f.get("rule_id") == "REMOVED_AUTH_MIDDLEWARE" for f in decision["deterministic_findings"]), "REMOVED_AUTH_MIDDLEWARE rule missing"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
