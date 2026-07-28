from __future__ import annotations

import unittest
from unittest.mock import MagicMock

from incident_history.models import SimilarIncident, LLMResult
from incident_history.retrieval.ranking import rank_incidents
from incident_history.service import IncidentHistoryService, _confidence, _confidence_explanation
from incident_history.llm.reasoner import IncidentLLMReasoner, _build_prompt


class TestHistoricalReasoning(unittest.TestCase):
    def setUp(self):
        self.sample_incidents = [
            SimilarIncident(
                incident_id="INC-2001",
                similarity=0.88,
                severity="critical",
                outcome="Rollback",
                title="Container Privilege Escalation via USER root in Dockerfile",
                description="The Dockerfile explicitly set USER root.",
                root_cause="Executing processes as UID 0 instead of unprivileged user.",
                impact="Full container compromise, exfiltration of local secrets.",
                resolution="Rebuilt image with appuser (UID 10001) and rolled back.",
                tags=["docker", "root", "privilege-escalation"],
            ),
            SimilarIncident(
                incident_id="INC-2030",
                similarity=0.85,
                severity="critical",
                outcome="Security Incident",
                title="Public S3 Bucket Exposure via Public-Read ACL in Terraform",
                description="Terraform set acl = 'public-read' on bucket.",
                root_cause="Terraform IaC misconfiguration enabling public read access.",
                impact="Exposure of 15,000 customer export documents.",
                resolution="Reverted ACL to private and enabled S3 Block Public Access.",
                tags=["terraform", "s3", "public-bucket"],
            ),
            SimilarIncident(
                incident_id="INC-2031",
                similarity=0.82,
                severity="critical",
                outcome="Security Incident",
                title="Wildcard IAM Admin Policy Attachment via Terraform",
                description="Terraform IAM policy assigned Action: '*' and Resource: '*'.",
                root_cause="Wildcard IAM permissions in Terraform module.",
                impact="Full AWS account administrator access granted to Lambda role.",
                resolution="Replaced wildcard policy with specific S3 permissions.",
                tags=["terraform", "iam", "wildcard-policy"],
            ),
            SimilarIncident(
                incident_id="INC-2020",
                similarity=0.89,
                severity="critical",
                outcome="Security Incident",
                title="Privileged Pod SecurityContext Breakout in Production Kubernetes",
                description="Setting securityContext.privileged: true in deployment.",
                root_cause="Privileged security context enabled on K8s pod manifest.",
                impact="Node compromise and cross-pod data access risk.",
                resolution="Enforced Kyverno Pod Security Standard Restricted profile.",
                tags=["kubernetes", "privileged-pod", "container-escape"],
            ),
            SimilarIncident(
                incident_id="INC-2041",
                similarity=0.87,
                severity="critical",
                outcome="Security Incident",
                title="Plaintext Secrets Echoed to GitHub Actions Build Logs",
                description="Workflow run step executed echo ${{ secrets.PROD_KEY }}.",
                root_cause="Direct use of echo on secret variables.",
                impact="Exposure of production SSH key in Actions log archive.",
                resolution="Deleted workflow run log history and rotated SSH key pair.",
                tags=["github-actions", "secrets-echo", "secret-leak"],
            ),
            SimilarIncident(
                incident_id="INC-2060",
                similarity=0.86,
                severity="critical",
                outcome="Rollback",
                title="Authentication Middleware Removal Causes Unauthenticated Access",
                description="Refactoring removed @require_auth decorator.",
                root_cause="Omission of authentication guard decorator.",
                impact="Unauthenticated modification of user profiles.",
                resolution="Re-added @require_auth guard and added integration test.",
                tags=["authentication", "auth-bypass", "missing-decorator"],
            ),
        ]

    def test_docker_privilege_escalation_scenario(self):
        docker_incidents = [i for i in self.sample_incidents if "docker" in i.tags]
        ranked = rank_incidents(docker_incidents, query_text="Dockerfile USER root privileged")
        self.assertTrue(len(ranked) > 0)
        self.assertEqual(ranked[0].incident_id, "INC-2001")
        self.assertIn("uid 0", ranked[0].root_cause.lower())

    def test_public_s3_exposure_scenario(self):
        s3_incidents = [i for i in self.sample_incidents if "s3" in i.tags]
        ranked = rank_incidents(s3_incidents, query_text="terraform aws_s3_bucket acl = public-read")
        self.assertTrue(len(ranked) > 0)
        self.assertEqual(ranked[0].incident_id, "INC-2030")
        self.assertIn("public", ranked[0].root_cause.lower())

    def test_wildcard_iam_policy_scenario(self):
        iam_incidents = [i for i in self.sample_incidents if "iam" in i.tags]
        ranked = rank_incidents(iam_incidents, query_text="terraform aws_iam_policy Action *")
        self.assertTrue(len(ranked) > 0)
        self.assertEqual(ranked[0].incident_id, "INC-2031")
        self.assertIn("wildcard", ranked[0].root_cause.lower())

    def test_kubernetes_privileged_pod_scenario(self):
        k8s_incidents = [i for i in self.sample_incidents if "kubernetes" in i.tags]
        ranked = rank_incidents(k8s_incidents, query_text="kubernetes securityContext privileged true")
        self.assertTrue(len(ranked) > 0)
        self.assertEqual(ranked[0].incident_id, "INC-2020")
        self.assertIn("privileged", ranked[0].root_cause.lower())

    def test_github_actions_secret_leak_scenario(self):
        gha_incidents = [i for i in self.sample_incidents if "github-actions" in i.tags]
        ranked = rank_incidents(gha_incidents, query_text="github actions echo secrets.PROD_KEY")
        self.assertTrue(len(ranked) > 0)
        self.assertEqual(ranked[0].incident_id, "INC-2041")
        self.assertIn("secret", ranked[0].root_cause.lower())

    def test_authentication_regression_scenario(self):
        auth_incidents = [i for i in self.sample_incidents if "authentication" in i.tags]
        ranked = rank_incidents(auth_incidents, query_text="removed require_auth decorator")
        self.assertTrue(len(ranked) > 0)
        self.assertEqual(ranked[0].incident_id, "INC-2060")
        self.assertIn("auth", ranked[0].root_cause.lower())

    def test_clean_deployment_scenario(self):
        conf, factors = _confidence(incidents=[], qdrant_available=True, embedding_quality="ok")
        explanation = _confidence_explanation(conf, incidents=[], qdrant_available=True)
        self.assertEqual(conf, 0.92)
        self.assertIn("clean record", factors[-1].lower())
        self.assertIn("0.92", explanation)

    def test_prompt_builder_includes_comparison_fields(self):
        prompt = _build_prompt("PR diff content", {"score": 50}, self.sample_incidents[:2])
        self.assertIn("What happened before?", prompt)
        self.assertIn("How similar is this PR?", prompt)
        self.assertIn("What is different?", prompt)
        self.assertIn("What can we learn?", prompt)
        self.assertIn("common_failure_pattern", prompt)
        self.assertIn("risk_comparison", prompt)


if __name__ == "__main__":
    unittest.main()
