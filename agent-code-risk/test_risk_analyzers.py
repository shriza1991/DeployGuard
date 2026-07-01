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
        self.assertGreaterEqual(analysis["confidence"], 60)
        self.assertTrue(any("authentication" in reason.lower() or "security" in reason.lower() for reason in analysis["reasons"]))
        self.assertTrue(analysis["recommendations"])


if __name__ == "__main__":
    unittest.main()
