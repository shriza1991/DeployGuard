import os
import sys
import unittest
from unittest.mock import MagicMock, patch

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(ROOT_DIR, "aggregator"))
sys.path.insert(0, os.path.join(ROOT_DIR, "agent-code-risk"))


from config import Settings
from aggregation_engine import AggregationEngine
from repository_context_client import wait_for_readiness


class TestOrchestrationRedesign(unittest.TestCase):
    def setUp(self):
        self.settings = Settings(
            timeout_seconds=90,
            expected_agents_str="code-risk,infra-risk,incident-history"
        )
        self.mock_redis = MagicMock()
        self.mock_publisher = MagicMock()
        self.engine = AggregationEngine(self.settings, self.mock_redis, self.mock_publisher)

    def test_settings_expected_agents(self):
        self.assertEqual(self.settings.timeout_seconds, 90)
        self.assertEqual(self.settings.expected_agents, {"code-risk", "infra-risk", "incident-history"})

    def test_event_driven_aggregation_when_all_agents_respond(self):
        cid = "test-corr-1"
        self.mock_redis.get_final_decision.return_value = None
        self.mock_redis.delete_timeout_marker.return_value = True

        results = {
            "code-risk": {"score": 10, "severity": "low", "confidence": 0.9, "duration_ms": 300.0, "metadata": {"code_risk_ms": 300.0, "repository_context_ms": 150.0}},
            "infra-risk": {"score": 5, "severity": "low", "confidence": 0.95, "duration_ms": 200.0, "metadata": {"infra_risk_ms": 200.0}},
            "incident-history": {"score": 0, "severity": "low", "confidence": 0.99, "duration_ms": 100.0, "metadata": {"incident_history_ms": 100.0}}
        }
        self.mock_redis.get_agent_results.return_value = results
        self.mock_redis.get_deployment_meta.return_value = {"webhook_ms": 25.0}

        self.engine.handle_agent_result(cid, "incident-history", results["incident-history"])

        self.mock_publisher.publish.assert_called_once()
        published_cid, decision = self.mock_publisher.publish.call_args[0]
        self.assertEqual(published_cid, cid)
        self.assertIn("timings", decision["metadata"])
        timings = decision["metadata"]["timings"]
        self.assertEqual(timings["webhook_ms"], 25.0)
        self.assertEqual(timings["repository_context_ms"], 150.0)
        self.assertEqual(timings["code_risk_ms"], 300.0)
        self.assertEqual(timings["infra_risk_ms"], 200.0)
        self.assertEqual(timings["incident_history_ms"], 100.0)
        self.assertIn("total_pipeline_ms", timings)

        # Verify agent states
        self.assertEqual(decision["metadata"]["agent_states"], {
            "code-risk": "COMPLETED",
            "infra-risk": "COMPLETED",
            "incident-history": "COMPLETED"
        })

    def test_late_result_recorded_without_altering_decision(self):
        cid = "test-corr-2"
        # Decision already exists!
        self.mock_redis.get_final_decision.return_value = {"decision": "SAFE", "overall_score": 10}

        late_payload = {"score": 90, "severity": "critical", "confidence": 0.9}
        self.engine.handle_agent_result(cid, "code-risk", late_payload)

        # Verify late result is saved to Redis for audit
        self.mock_redis.save_agent_result.assert_called_with(cid, "code-risk", late_payload)
        # Verify decision publisher was NOT called (no re-aggregation)
        self.mock_publisher.publish.assert_not_called()

    def test_timeout_aggregation_marks_missing_agents(self):
        cid = "test-corr-3"
        self.mock_redis.scan_iter.return_value = [b"timeout:test-corr-3"]
        self.mock_redis.client.scan_iter.return_value = [b"timeout:test-corr-3"]
        self.mock_redis.client.get.return_value = b"100.0"
        self.mock_redis.get_final_decision.return_value = None
        self.mock_redis.delete_timeout_marker.return_value = True

        partial_results = {
            "incident-history": {"score": 5, "severity": "low", "confidence": 0.9, "duration_ms": 80.0}
        }
        self.mock_redis.get_agent_results.return_value = partial_results

        with patch("time.time", return_value=200.0):  # 100s elapsed > 90s
            self.engine.process_timeouts()

        self.mock_publisher.publish.assert_called_once()
        _, decision = self.mock_publisher.publish.call_args[0]
        states = decision["metadata"]["agent_states"]
        self.assertEqual(states["incident-history"], "COMPLETED")
        self.assertEqual(states["code-risk"], "TIMED_OUT")
        self.assertEqual(states["infra-risk"], "TIMED_OUT")

    @patch("time.sleep", return_value=None)
    @patch("requests.get")
    def test_code_risk_wait_for_readiness_backoff(self, mock_get, mock_sleep):
        # 1st call: LOADING_MODEL, 2nd call: READY
        res1 = MagicMock(status_code=200)
        res1.json.return_value = {"state": "LOADING_MODEL", "ready": False}

        res2 = MagicMock(status_code=200)
        res2.json.return_value = {"state": "READY", "ready": True}

        mock_get.side_effect = [res1, res2]

        is_ready = wait_for_readiness(max_wait_seconds=10.0, initial_backoff=0.1)
        self.assertTrue(is_ready)
        self.assertEqual(mock_get.call_count, 2)


if __name__ == "__main__":
    unittest.main()
