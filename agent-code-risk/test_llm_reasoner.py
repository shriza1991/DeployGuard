import unittest

from llm_reasoner import _default_response, _normalize_response


class LLMReasonerTests(unittest.TestCase):
    def test_normalizes_reasoning_output_to_safe_shape(self):
        response = _normalize_response(
            {
                "summary": "Rollout should be cautious",
                "additional_risks": ["Backwards compatibility risk"],
                "deployment_recommendation": "Use canary deployment",
                "confidence_adjustment": 0.08,
                "risk_adjustment": 5,
                "reasoning": "The change touches auth and infra config",
            }
        )

        self.assertTrue(response["available"])
        self.assertEqual(response["summary"], "Rollout should be cautious")
        self.assertEqual(response["risk_adjustment"], 5)
        self.assertEqual(response["confidence_adjustment"], 0.08)

    def test_default_response_is_used_when_unavailable(self):
        response = _default_response()
        self.assertFalse(response["available"])
        self.assertIn("deterministic", response["summary"].lower())


if __name__ == "__main__":
    unittest.main()
