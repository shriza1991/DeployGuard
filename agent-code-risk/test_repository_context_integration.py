import unittest
from unittest.mock import patch, MagicMock
import requests
import json
import time

from repository_context_client import RepositoryEvidenceProvider
from llm.context_assembly import assemble_context, Evidence, AssembledContext
from llm.prompt_builder import build_prompt

class TestRepositoryContextIntegration(unittest.TestCase):
    def setUp(self):
        self.mock_payload = {
            "repository": {
                "name": "DeployGuard",
                "full_name": "shriza1991/DeployGuard"
            },
            "pull_request": {
                "title": "Fix auth vulnerability",
                "body": "This patches authentication middleware",
                "head": {"ref": "patch-auth"},
                "url": "https://github.com/shriza1991/DeployGuard/pull/1"
            },
            "head_commit": {
                "message": "Auth hotfix commit"
            },
            "files": [
                {
                    "filename": "gateway/main.py",
                    "patch": "@@ -1 +1 @@\n-auth = None\n+auth = True"
                },
                {
                    "filename": "aggregator/consumer.py",
                    "patch": "@@ -1 +1 @@\n-process()\n+process_safe()"
                }
            ]
        }
        self.mock_deterministic_result = {
            "score": 65,
            "severity": "high",
            "confidence": 80,
            "reasons": ["Modified authentication logic", "Contains secret pattern"],
            "recommendations": ["Audit before merge"],
            "metadata": {"analyzer": "code-analyzer"}
        }

    @patch("requests.post")
    def test_client_payload_parsing_and_success(self, mock_post):
        # Mock successful response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "results": [
                {
                    "score": 0.85,
                    "text": "def validate_token(): pass",
                    "metadata": {
                        "relative_path": "gateway/auth.py",
                        "start_line": 1,
                        "end_line": 10,
                        "kind": "source"
                    }
                }
            ]
        }
        mock_post.return_value = mock_response

        evidence, metrics = RepositoryEvidenceProvider.get_repository_evidence(self.mock_payload)
        
        self.assertEqual(len(evidence), 1)
        self.assertEqual(evidence[0]["score"], 0.85)
        self.assertTrue(metrics["repository_context_available"])
        self.assertEqual(metrics["retrieved_chunks"], 1)

        # Verify post payload
        args, kwargs = mock_post.call_args
        json_data = kwargs["json"]
        self.assertEqual(json_data["repository"], "DeployGuard")
        self.assertEqual(json_data["branch"], "patch-auth")
        self.assertIn("gateway/main.py", json_data["changed_files"])
        self.assertIn("Fix auth vulnerability", json_data["pr_title"])
        self.assertIn("Auth hotfix commit", json_data["commit_message"])
        self.assertIn("--- a/gateway/main.py", json_data["diff"])

    @patch("requests.post")
    def test_client_timeout_handling(self, mock_post):
        # Mock timeout exception
        mock_post.side_effect = requests.Timeout("Connection timed out")

        evidence, metrics = RepositoryEvidenceProvider.get_repository_evidence(self.mock_payload)
        
        self.assertEqual(evidence, [])
        self.assertFalse(metrics["repository_context_available"])
        self.assertEqual(metrics["retrieved_chunks"], 0)

    @patch("requests.post")
    def test_client_malformed_json(self, mock_post):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.side_effect = ValueError("Malformed JSON")
        mock_post.return_value = mock_response

        evidence, metrics = RepositoryEvidenceProvider.get_repository_evidence(self.mock_payload)
        
        self.assertEqual(evidence, [])
        self.assertFalse(metrics["repository_context_available"])

    def test_context_assembly_limits_and_truncation(self):
        # Create 12 mock evidence chunks (exceeds limit of 10)
        raw_evidence = []
        for i in range(12):
            raw_evidence.append({
                "score": 0.90,
                "text": "A" * 800,  # 800 chars per text, 10 * 800 = 8000 (exceeds 7000 limit)
                "metadata": {
                    "relative_path": f"src/file_{i}.py",
                    "start_line": 1,
                    "end_line": 50,
                    "kind": "source"
                }
            })

        metrics = {
            "retrieval_latency_ms": 10.0,
            "retrieved_chunks": 12,
            "repository_context_available": True
        }

        context = assemble_context(
            payload=self.mock_payload,
            deterministic_result=self.mock_deterministic_result,
            raw_evidence=raw_evidence,
            metrics=metrics
        )

        self.assertEqual(context.repository, "DeployGuard")
        self.assertEqual(context.branch, "patch-auth")
        
        # Verify chunks capped at 10 and characters capped at 7000
        self.assertTrue(len(context.evidence_list) <= 10)
        self.assertTrue(metrics["total_characters"] <= 7000)
        self.assertTrue(metrics["context_truncated"])

    def test_prompt_builder_extended_formatting(self):
        evidence_list = [
            Evidence(
                text="class TokenHandler:",
                source="repository",
                metadata={
                    "file_path": "gateway/auth.py",
                    "lines": "10-25",
                    "kind": "source",
                    "score": 0.95,
                    "repository": "DeployGuard",
                    "branch": "main"
                }
            )
        ]
        context = AssembledContext(
            score=45,
            severity="medium",
            confidence=90,
            reasons=["Mock reason"],
            recommendations=["Mock rec"],
            changed_files=[{"filename": "app.py", "patch": "diff"}],
            metadata={},
            pr_title="PR title",
            pr_description="PR desc",
            commit_message="commit msg",
            repository="DeployGuard",
            branch="main",
            evidence_list=evidence_list
        )

        prompt = build_prompt(context)
        
        self.assertIn("Repository Context Summary", prompt)
        self.assertIn("Files involved:", prompt)
        self.assertIn("gateway/auth.py", prompt)
        self.assertIn("Related components:", prompt)
        self.assertIn("File: gateway/auth.py", prompt)
        self.assertIn("Matched chunk:", prompt)
        self.assertIn("class TokenHandler:", prompt)
        self.assertIn("PR Metadata", prompt)
        self.assertIn("PR title", prompt)
        self.assertIn("PR desc", prompt)
        self.assertIn("commit msg", prompt)

    def test_prompt_builder_backward_compatibility(self):
        # Call build_prompt using old positional arguments
        prompt = build_prompt(
            score=30,
            severity="low",
            confidence=50,
            reasons=["Low findings"],
            recommendations=["No recommendation"],
            changed_files=[{"filename": "app.py", "patch": "diff"}],
            metadata={"source": "test"}
        )

        # Extended blocks must NOT be present
        self.assertNotIn("Repository Context Summary", prompt)
        self.assertNotIn("Relevant Repository Evidence", prompt)
        # Original block elements must be present
        self.assertIn("Deterministic Security Findings", prompt)
        self.assertIn("Score  : 30", prompt)
        self.assertIn("Severity: low", prompt)

if __name__ == "__main__":
    unittest.main()
