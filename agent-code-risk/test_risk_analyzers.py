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


    def test_authentication_analyzer_filters(self):
        # 1. Test file: should be ignored and not trigger CODE_AUTH_MODIFIED
        payload_test_file = {
            "files": [
                {
                    "filename": "tests/test_login.py",
                    "patch": "@@ -1 +1 @@\n+jwt.decode(token)\n",
                }
            ]
        }
        analysis = analyze_code_risk(payload_test_file)
        self.assertNotIn("CODE_AUTH_MODIFIED", [f.get("rule_id") for f in analysis.get("deterministic_findings", [])])

        # 2. Keywords inside HTTP URLs, assertions, comments, or string literals: should be ignored
        payload_false_positives = {
            "files": [
                {
                    "filename": "app/auth.py",
                    "patch": "@@ -1,5 +1 @@\n-# check user session role token\n-url = 'https://example.com/auth/login'\n-request_path = '/login'\n-assert token == 'secret'\n-expect(auth).toBeDefined()\n",
                }
            ]
        }
        analysis = analyze_code_risk(payload_false_positives)
        self.assertNotIn("CODE_AUTH_MODIFIED", [f.get("rule_id") for f in analysis.get("deterministic_findings", [])])

        # 3. Strong evidence: should trigger CODE_AUTH_MODIFIED
        payload_true_positive = {
            "files": [
                {
                    "filename": "app/auth.py",
                    "patch": "@@ -1 +1 @@\n+jwt.decode(token)\n",
                }
            ]
        }
        analysis = analyze_code_risk(payload_true_positive)
        self.assertTrue(any(f.get("rule_id") == "CODE_AUTH_MODIFIED" for f in analysis.get("deterministic_findings", [])))


    def test_security_sensitive_analyzer_filters(self):
        # 1. Test file and HTTP request URL inside test: should be ignored and not trigger CODE_SECURITY_SENSITIVE
        payload_test_file = {
            "files": [
                {
                    "filename": "backend/tests/test_validation.py",
                    "patch": "@@ -1 +1 @@\n+client.post(\"/api/v1/auth/login\", headers=headers)\n",
                }
            ]
        }
        analysis = analyze_code_risk(payload_test_file)
        self.assertNotIn("CODE_SECURITY_SENSITIVE", [f.get("rule_id") for f in analysis.get("deterministic_findings", [])])

        # 2. Keywords inside HTTP URLs, string literals, comments, or assertions: should be ignored
        payload_false_positives = {
            "files": [
                {
                    "filename": "app/utils.py",
                    "patch": "@@ -1,5 +1 @@\n-# check encryption key and security\n-url = 'https://example.com/api/v1/auth/login'\n-msg = 'jwt.decode authentication failed'\n-assert token == 'secret'\n-expect(security).toBeDefined()\n",
                }
            ]
        }
        analysis = analyze_code_risk(payload_false_positives)
        self.assertNotIn("CODE_SECURITY_SENSITIVE", [f.get("rule_id") for f in analysis.get("deterministic_findings", [])])

        # 3. Strong evidence: should trigger CODE_SECURITY_SENSITIVE
        payload_true_positive = {
            "files": [
                {
                    "filename": "app/crypto.py",
                    "patch": "@@ -1 +1 @@\n+cipher = AES.new(key)\n",
                }
            ]
        }
        analysis = analyze_code_risk(payload_true_positive)
        self.assertTrue(any(f.get("rule_id") == "CODE_SECURITY_SENSITIVE" for f in analysis.get("deterministic_findings", [])))


if __name__ == "__main__":
    unittest.main()
