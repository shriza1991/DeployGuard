import unittest

from risk_analyzers import analyze_infra_risk


class InfraRiskAnalyzerTests(unittest.TestCase):
    def test_metadata_only_deployment_triggers_critical_infra_findings(self):
        payload = {
            "pull_request": {
                "title": "Deploy production infrastructure with privileged Docker container and public AWS resources",
                "body": (
                    "Docker containers run as root and use latest image tags. "
                    "Kubernetes enables privileged mode, hostNetwork and hostPath. "
                    "Terraform creates a public S3 bucket and opens 22 and 3306 to 0.0.0.0/0. "
                    "AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY were added for testing. "
                    "GitHub Actions uses unpinned actions and prints secrets."
                ),
            },
            "head_commit": {"message": "Added privileged Docker deployment AWS_ACCESS_KEY_ID=AKIA_TEST123"},
        }

        analysis = analyze_infra_risk(payload)
        reasons = " ".join(analysis["reasons"]).lower()

        self.assertGreater(analysis["score"], 90)
        self.assertEqual(analysis["severity"], "critical")
        for expected in (
            "privileged docker",
            "runs as root",
            "latest tag",
            "public s3 bucket",
            "open security groups",
            "aws credentials",
            "hostnetwork",
            "hostpath",
            "unpinned action",
        ):
            self.assertIn(expected, reasons)


if __name__ == "__main__":
    unittest.main()
