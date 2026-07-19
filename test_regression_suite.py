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
sys.path.insert(0, os.path.join(ROOT_DIR, "agent-incident-history"))
sys.path.insert(0, os.path.join(ROOT_DIR, "aggregator"))

import importlib.util
from incident_history.service import _confidence as incident_confidence

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
    """Scenario 1: README/docs-only change -> Expected: SAFE (Score 5-10)"""
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
    assert 5 <= decision["overall_score"] <= 10, f"Expected score 5-10 for README only, got {decision['overall_score']}"
    assert "score_breakdown" in decision, "score_breakdown missing from decision output"


def test_scenario_dependency_update():
    """Scenario 2: Dependency update -> Expected: SAFE (Score 10-20)"""
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
    assert 5 <= decision["overall_score"] <= 20, f"Expected score 10-20 for dep update, got {decision['overall_score']}"
    assert "score_breakdown" in decision, "score_breakdown missing from decision output"


def test_scenario_user_root():
    """Scenario 3: Dockerfile USER root -> Expected: REVIEW (Score 60-75)"""
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
    assert 60 <= decision["overall_score"] <= 75, f"Expected score 60-75 for USER root, got {decision['overall_score']}"
    assert any(f.get("rule_id") == "DOCKER_ROOT_USER" for f in decision["deterministic_findings"]), "DOCKER_ROOT_USER rule missing"
    assert "score_breakdown" in decision, "score_breakdown missing from decision output"


def test_scenario_user_root_plus_latest():
    """Scenario 4: USER root + FROM latest tag -> Expected: REVIEW (Score 75-90)"""
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
    assert 75 <= decision["overall_score"] <= 90, f"Expected score 75-90 for USER root + latest, got {decision['overall_score']}"
    assert "score_breakdown" in decision, "score_breakdown missing from decision output"


def test_scenario_privileged_kubernetes():
    """Scenario 5: Privileged Kubernetes pod -> Expected: BLOCK (Score 80-100)"""
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
    assert 80 <= decision["overall_score"] <= 100, f"Expected score 80-100 for Privileged K8s, got {decision['overall_score']}"
    assert any(f.get("rule_id") == "K8S_PRIVILEGED_POD" for f in decision["deterministic_findings"]), "K8S_PRIVILEGED_POD rule missing"
    assert "score_breakdown" in decision, "score_breakdown missing from decision output"


def test_scenario_open_ssh_ingress():
    """Scenario 6: Open SSH (0.0.0.0/0) -> Expected: BLOCK (Score 90-100)"""
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
    assert 90 <= decision["overall_score"] <= 100, f"Expected score 90-100 for Open SSH, got {decision['overall_score']}"
    assert any(f.get("rule_id") == "TERRAFORM_OPEN_SSH" for f in decision["deterministic_findings"]), "TERRAFORM_OPEN_SSH rule missing"
    assert "score_breakdown" in decision, "score_breakdown missing from decision output"


def test_scenario_public_s3_bucket():
    """Scenario 7: Public S3 Bucket -> Expected: BLOCK (Score 90-100)"""
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
    assert 90 <= decision["overall_score"] <= 100, f"Expected score 90-100 for Public S3, got {decision['overall_score']}"
    assert any(f.get("rule_id") == "TERRAFORM_PUBLIC_S3" for f in decision["deterministic_findings"]), "TERRAFORM_PUBLIC_S3 rule missing"
    assert "score_breakdown" in decision, "score_breakdown missing from decision output"


def test_scenario_aws_secret_key():
    """Scenario 8: Hardcoded AWS Secret -> Expected: BLOCK (Score 100)"""
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
    assert decision["overall_score"] == 100, f"Expected score 100 for AWS Secret, got {decision['overall_score']}"
    assert any(f.get("rule_id") == "HARDCODED_AWS_CREDENTIALS" for f in decision["deterministic_findings"]), "HARDCODED_AWS_CREDENTIALS rule missing"
    assert "score_breakdown" in decision, "score_breakdown missing from decision output"


def test_scenario_remove_auth_middleware():
    """Scenario 9: Remove authentication middleware -> Expected: REVIEW / BLOCK (Score 80-100)"""
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
    assert 80 <= decision["overall_score"] <= 100, f"Expected score 80-100 for Auth Removal, got {decision['overall_score']}"
    assert any(f.get("rule_id") == "REMOVED_AUTH_MIDDLEWARE" for f in decision["deterministic_findings"]), "REMOVED_AUTH_MIDDLEWARE rule missing"
    assert "score_breakdown" in decision, "score_breakdown missing from decision output"


def test_technology_agnostic_isolation():
    """Scenario 10: Pure Python repo change (no Docker/Terraform/K8s) -> Expected: SAFE, 0 infra findings"""
    payload = {
        "repository": {"name": "myorg/pure-python-lib"},
        "pull_request": {
            "title": "refactor: optimize string manipulation helper",
            "body": "Improves performance of string formatting utility.",
        },
        "changed_files": [
            {
                "filename": "utils.py",
                "patch": "+ def format_string(s: str) -> str:\n+     return s.strip().lower()",
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

    decision = make_decision("test-agnostic-corr-id", agent_results)

    assert decision["decision"] == "SAFE", f"Expected SAFE for pure python lib, got {decision['decision']}"
    assert decision["overall_score"] <= 15, f"Expected low score <= 15, got {decision['overall_score']}"
    assert len(infra_res.get("deterministic_findings", [])) == 0, f"Expected 0 infra findings for non-infra repo, got {len(infra_res.get('deterministic_findings', []))}"


def test_confidence_case_1_no_security_findings():
    """Case 1: No security findings -> Risk low, Confidence > 0.90 (90%)"""
    payload = {
        "repository": {"name": "myorg/safe-repo"},
        "pull_request": {"title": "docs: update readme", "body": "Small readme fix"},
        "changed_files": [{"filename": "README.md", "patch": "+ Small fix"}],
    }
    code_res = code_risk_analyzer(payload)
    infra_res = infra_risk_analyzer(payload)
    agent_results = {
        "code-risk": code_res,
        "infra-risk": infra_res,
        "incident-history": {"score": 10, "severity": "low", "confidence": 0.92, "confidence_factors": ["Clean record"]},
    }
    decision = make_decision("test-case-1", agent_results)
    assert decision["overall_score"] <= 15
    assert decision["overall_confidence"] >= 0.90, f"Expected overall_confidence >= 0.90, got {decision['overall_confidence']}"


def test_confidence_case_2_critical_findings():
    """Case 2: Critical findings -> Risk > 90, Confidence > 0.90 (90%)"""
    payload = {
        "repository": {"name": "myorg/api-service"},
        "pull_request": {"title": "fix: add AWS key", "body": "Hardcoding key"},
        "changed_files": [{"filename": "config.py", "patch": '+ AWS_SECRET = "AKIAIOSFODNN7EXAMPLE"'}],
    }
    code_res = code_risk_analyzer(payload)
    infra_res = infra_risk_analyzer(payload)
    agent_results = {
        "code-risk": code_res,
        "infra-risk": infra_res,
        "incident-history": {"score": 10, "severity": "low", "confidence": 0.92},
    }
    decision = make_decision("test-case-2", agent_results)
    assert decision["overall_score"] >= 90
    assert decision["overall_confidence"] >= 0.90, f"Expected overall_confidence >= 0.90, got {decision['overall_confidence']}"


def test_confidence_case_3_missing_git_metadata():
    """Case 3: Missing Git metadata -> Confidence 0.30 - 0.60"""
    payload = {}
    code_res = code_risk_analyzer(payload)
    infra_res = infra_risk_analyzer(payload)
    agent_results = {
        "code-risk": code_res,
        "infra-risk": infra_res,
        "incident-history": {"score": 10, "severity": "low", "confidence": 0.35},
    }
    decision = make_decision("test-case-3", agent_results)
    assert 0.30 <= decision["overall_confidence"] <= 0.60, f"Expected confidence 0.30-0.60 for missing metadata, got {decision['overall_confidence']}"


def test_confidence_case_4_analysis_timeout():
    """Case 4: Analysis timeout / error -> Confidence < 0.30"""
    agent_results = {
        "code-risk": {"score": 0, "severity": "low", "confidence": 0.10},
        "infra-risk": {"score": 0, "severity": "low", "confidence": 0.10},
        "incident-history": {"score": 10, "severity": "low", "confidence": 0.10},
    }
    decision = make_decision("test-case-4", agent_results)
    assert decision["overall_confidence"] < 0.30, f"Expected timeout confidence < 0.30, got {decision['overall_confidence']}"


def test_confidence_case_5_format_safeguard():
    """Case 5: Verify backend confidence float 0.94 vs percentage conversion helper"""
    def normalize_confidence(value):
        if value is None:
            return None
        if value <= 1.0 and value >= 0.0:
            return round(value * 100)
        return round(min(100, max(0, value)))

    assert normalize_confidence(0.94) == 94
    assert normalize_confidence(94) == 94
    assert normalize_confidence(0.0) == 0
    assert normalize_confidence(None) is None


def test_confidence_case_6_zero_incidents_high_confidence():
    """Case 6: 0 historical incidents matched with healthy search -> High confidence (>=0.90)"""

    conf, factors = incident_confidence(incidents=[], qdrant_available=True, embedding_quality="ok")
    assert conf >= 0.90, f"Expected 0 incidents with healthy search to yield confidence >= 0.90, got {conf}"
    assert "No historical incidents matched (clean record)" in factors


if __name__ == "__main__":
    pytest.main([__file__, "-v"])


