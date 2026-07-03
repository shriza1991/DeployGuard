import unittest

from llm_reasoner import _default_response, _normalize_response


class LLMReasonerTests(unittest.TestCase):
    def test_normalizes_reasoning_output_to_safe_shape(self):
        response = _normalize_response(
            {
                "summary": "Rollout should be cautious",
                "risk_reasoning": ["Backwards compatibility risk"],
                "recommendations": ["Use canary deployment"],
                "confidence": 0.08,
                "available": True,
            },
            provider_name="gemini",
        )

        self.assertTrue(response["available"])
        self.assertEqual(response["summary"], "Rollout should be cautious")
        self.assertEqual(response["confidence"], 0.08)
        self.assertEqual(response["provider"], "gemini")

    def test_default_response_is_used_when_unavailable(self):
        response = _default_response(provider_name="unavailable")
        self.assertFalse(response["available"])
        self.assertEqual(response["provider"], "unavailable")
        self.assertEqual(response["summary"], "")


if __name__ == "__main__":
    unittest.main()
