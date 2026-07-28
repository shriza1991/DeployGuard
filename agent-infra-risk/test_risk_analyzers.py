import unittest
from unittest.mock import patch, MagicMock

from risk_analyzers import analyze_infra_risk, _classify_file


class InfraRiskAnalyzerTests(unittest.TestCase):
    def test_nested_infrastructure_paths_classification(self):
        test_cases = [
            ("docker/Dockerfile", True, ["docker"], "docker"),
            ("docker/docker-compose.yml", True, ["docker_compose"], "docker_compose"),
            (".github/workflows/ci.yml", True, ["github_actions"], "github_actions"),
            ("kubernetes/deployment.yaml", True, ["kubernetes"], "kubernetes"),
            ("k8s/deployment.yaml", True, ["kubernetes"], "kubernetes"),
            ("terraform/main.tf", True, ["terraform"], "terraform"),
            ("infra/main.tf", True, ["terraform"], "terraform"),
            ("helm/chart/values.yaml", True, ["kubernetes"], "kubernetes"),
            ("README.md", False, [], "skipped"),
            ("backend/auth.py", False, [], "skipped"),
        ]

        for filepath, expected_is_infra, expected_analyzers, expected_category in test_cases:
            with self.subTest(filepath=filepath):
                is_infra, analyzers, category, display_or_reason = _classify_file(filepath)
                self.assertEqual(is_infra, expected_is_infra, f"Failed is_infra check for {filepath}")
                self.assertEqual(analyzers, expected_analyzers, f"Failed analyzers check for {filepath}")
                self.assertEqual(category, expected_category, f"Failed category check for {filepath}")

    def test_pr_with_nested_infra_files_analysis(self):
        payload = {
            "files": [
                {"filename": ".github/workflows/ci.yml", "patch": "+      uses: actions/checkout@main"},
                {"filename": "docker/Dockerfile", "patch": "+FROM python:3.11\n+USER root"},
                {"filename": "docker/docker-compose.yml", "patch": "+  privileged: true"},
                {"filename": "kubernetes/deployment.yaml", "patch": "+  containers:\n+  - securityContext:\n+      privileged: true"},
                {"filename": "terraform/main.tf", "patch": '+  acl = "public-read"'},
                {"filename": "README.md", "patch": "+ # Documentation update"},
                {"filename": "backend/auth.py", "patch": "+ def authenticate(): pass"},
            ]
        }

        analysis = analyze_infra_risk(payload)
        metadata = analysis.get("metadata", {})

        self.assertEqual(metadata.get("infra_files_analyzed"), 5)
        self.assertIn("docker/Dockerfile", metadata.get("infra_files", []))
        self.assertIn("docker/docker-compose.yml", metadata.get("infra_files", []))
        self.assertIn(".github/workflows/ci.yml", metadata.get("infra_files", []))
        self.assertIn("kubernetes/deployment.yaml", metadata.get("infra_files", []))
        self.assertIn("terraform/main.tf", metadata.get("infra_files", []))
        self.assertNotIn("README.md", metadata.get("infra_files", []))
        self.assertNotIn("backend/auth.py", metadata.get("infra_files", []))

        # Check findings from multiple detectors
        rule_ids = {f["rule_id"] for f in analysis.get("deterministic_findings", [])}
        self.assertIn("GHA_UNPINNED_ACTION", rule_ids)
        self.assertIn("DOCKER_ROOT_USER", rule_ids)
        self.assertIn("COMPOSE_PRIVILEGED", rule_ids)
        self.assertIn("K8S_PRIVILEGED", rule_ids)
        self.assertIn("TF_PUBLIC_S3", rule_ids)
        self.assertGreater(analysis["score"], 50)

    @patch("requests.get")
    def test_raw_github_webhook_api_fetching_integration(self, mock_requests_get):
        """Integration test: Raw GitHub pull_request webhook payload (no embedded file objects)

        Triggers GitHub API fetch (GET /repos/{owner}/{repo}/pulls/{number}/files) and verifies
        that Docker, Kubernetes, Terraform, GitHub Actions, and Docker Compose files reach InfraFileRouter.
        """
        raw_github_webhook_payload = {
            "action": "opened",
            "number": 42,
            "pull_request": {
                "number": 42,
                "title": "infra: update all container and IaC configs",
                "body": "Raw webhook event from GitHub without embedded files array",
                "changed_files": 5,
                "url": "https://api.github.com/repos/myorg/myrepo/pulls/42",
            },
            "repository": {
                "name": "myrepo",
                "full_name": "myorg/myrepo",
                "owner": {"login": "myorg"},
            },
        }

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = [
            {
                "filename": "docker/Dockerfile",
                "status": "modified",
                "patch": "+ FROM python:3.11-slim\n+ USER root",
            },
            {
                "filename": "docker/docker-compose.yml",
                "status": "modified",
                "patch": "+   privileged: true",
            },
            {
                "filename": ".github/workflows/ci.yml",
                "status": "modified",
                "patch": "+     uses: actions/checkout@main",
            },
            {
                "filename": "kubernetes/deployment.yaml",
                "status": "modified",
                "patch": "+   containers:\n+     - name: app\n+       securityContext:\n+         privileged: true",
            },
            {
                "filename": "terraform/main.tf",
                "status": "modified",
                "patch": '+   acl = "public-read"',
            },
        ]
        mock_requests_get.return_value = mock_response

        analysis = analyze_infra_risk(raw_github_webhook_payload)
        metadata = analysis.get("metadata", {})

        # Verify GitHub API was called with GET /repos/myorg/myrepo/pulls/42/files
        mock_requests_get.assert_called_once()
        call_url = mock_requests_get.call_args[0][0]
        self.assertEqual(call_url, "https://api.github.com/repos/myorg/myrepo/pulls/42/files")

        # Verify InfraFileRouter received all 5 files from the API call
        self.assertEqual(metadata.get("infra_files_analyzed"), 5)
        analyzed_files = metadata.get("infra_files", [])
        expected_files = [
            "docker/Dockerfile",
            "docker/docker-compose.yml",
            ".github/workflows/ci.yml",
            "kubernetes/deployment.yaml",
            "terraform/main.tf",
        ]
        for ef in expected_files:
            self.assertIn(ef, analyzed_files)

        # Verify detectors executed and emitted rule findings for each file
        rule_ids = {f["rule_id"] for f in analysis.get("deterministic_findings", [])}
        self.assertIn("DOCKER_ROOT_USER", rule_ids)
        self.assertIn("COMPOSE_PRIVILEGED", rule_ids)
        self.assertIn("GHA_UNPINNED_ACTION", rule_ids)
        self.assertIn("K8S_PRIVILEGED", rule_ids)
        self.assertIn("TF_PUBLIC_S3", rule_ids)
        self.assertGreater(analysis["score"], 50)


if __name__ == "__main__":
    unittest.main()
