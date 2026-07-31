import unittest

from risk_analyzers import analyze_code_risk


class CodeRiskAnalyzerTests(unittest.TestCase):
    def test_detects_high_risk_changes_from_patch_content(self):
        payload = {
            "pull_request": {
                "title": "Fix authentication flow",
                "body": "This change updates token handling",
                "url": "https://example.test/pr/1",
            },
            "head_commit": {"message": "Deploy auth hotfix"},
            "files": [
                {
                    "filename": "app/auth.py",
                    "patch": "@@ -1 +1 @@\n-validate_token(user)\n+authenticate(user, token)\n",
                },
                {
                    "filename": "config/.env",
                    "patch": "+API_KEY=super-secret-token\n",
                },
            ],
        }

        analysis = analyze_code_risk(payload)

        self.assertGreaterEqual(analysis["score"], 50)
        self.assertIn(analysis["severity"], {"high", "critical"})
        self.assertGreaterEqual(analysis["confidence"], 0.60)
        self.assertTrue(any("authentication" in reason.lower() or "security" in reason.lower() for reason in analysis["reasons"]))
        self.assertTrue(analysis["recommendations"])


    def test_deleted_validation_analyzer_filters(self):
        # 1. Test file: should be ignored and not trigger REMOVED_AUTH_MIDDLEWARE
        payload_test_file = {
            "files": [
                {
                    "filename": "tests/test_auth.py",
                    "patch": "@@ -1 +1 @@\n-validate_token(user)\n",
                }
            ]
        }
        analysis = analyze_code_risk(payload_test_file)
        self.assertNotIn("REMOVED_AUTH_MIDDLEWARE", [f.get("rule_id") for f in analysis.get("deterministic_findings", [])])

        # 2. Deleted comments/strings/URLs only: should be ignored
        payload_false_positives = {
            "files": [
                {
                    "filename": "app/auth.py",
                    "patch": "@@ -1,4 +1 @@\n-# validate_token(user)\n-print(\"calling validate_token\")\n-url = \"https://example.com/validate_token\"\n-x = auth\n",
                }
            ]
        }
        analysis = analyze_code_risk(payload_false_positives)
        self.assertNotIn("REMOVED_AUTH_MIDDLEWARE", [f.get("rule_id") for f in analysis.get("deterministic_findings", [])])

        # 3. Strong evidence: should trigger
        payload_true_positive = {
            "files": [
                {
                    "filename": "app/auth.py",
                    "patch": "@@ -1 +1 @@\n-validate_token(user)\n",
                }
            ]
        }
        analysis = analyze_code_risk(payload_true_positive)
        self.assertTrue(any(f.get("rule_id") == "REMOVED_AUTH_MIDDLEWARE" for f in analysis.get("deterministic_findings", [])))


if __name__ == "__main__":
    unittest.main()
