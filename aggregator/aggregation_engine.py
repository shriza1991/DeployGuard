import time
from typing import Any, Dict, Set

from redis_store import RedisStore
from kafka_producer import RiskDecisionPublisher
from decision_engine import make_decision
from logger import logger
from config import Settings


class AggregationEngine:
    def __init__(
        self,
        settings: Settings,
        redis_store: RedisStore,
        publisher: RiskDecisionPublisher,
    ):
        self.settings = settings
        self.redis_store = redis_store
        self.publisher = publisher

    @property
    def expected_agents(self) -> Set[str]:
        return self.settings.expected_agents

    def handle_agent_result(
        self,
        correlation_id: str,
        agent_name: str,
        payload: Dict[str, Any],
    ) -> None:

        if not correlation_id:
            logger.warning(
                f"Received result with missing correlation_id: {payload}"
            )
            return

        if agent_name not in self.expected_agents:
            logger.warning(
                f"Received result from unexpected agent '{agent_name}': {payload}"
            )
            return

        # Check if deployment decision has already been finalized
        if self.redis_store.get_final_decision(correlation_id):
            logger.info(
                f"[aggregator] Late result received from agent '{agent_name}' "
                f"for completed deployment {correlation_id}, recorded for audit without altering finalized decision."
            )
            # Store late result in Redis for audit/record-keeping
            self.redis_store.save_agent_result(correlation_id, agent_name, payload)
            return

        # Save result
        self.redis_store.save_agent_result(
            correlation_id,
            agent_name,
            payload,
        )

        # Create timeout marker (only first result creates it)
        self.redis_store.set_timeout_marker(
            correlation_id,
            time.time(),
        )

        # Get all accumulated results
        results = self.redis_store.get_agent_results(correlation_id)
        current_agents = set(results.keys())

        logger.info(
            f"Current results for {correlation_id}: {current_agents} (Expected: {self.expected_agents})"
        )

        # Aggregate immediately if all expected agents have responded
        if current_agents >= self.expected_agents:
            logger.info(
                f"All expected agents responded for "
                f"{correlation_id}. Triggering immediate event-driven aggregation."
            )
            self._aggregate_and_publish(
                correlation_id,
                results,
            )

    def _aggregate_and_publish(
        self,
        correlation_id: str,
        results: Dict[str, Dict[str, Any]],
    ) -> None:

        # Atomic lock using timeout marker deletion
        if not self.redis_store.delete_timeout_marker(correlation_id):
            logger.info(
                f"Aggregation already handled for {correlation_id}"
            )
            return

        try:
            started = time.perf_counter()

            # Retrieve webhook metadata for stage timing calculations
            meta = self.redis_store.get_deployment_meta(correlation_id) or {}
            webhook_ms = meta.get("webhook_ms", 0.0)

            code_risk_res = results.get("code-risk") or {}
            infra_risk_res = results.get("infra-risk") or {}
            incident_history_res = results.get("incident-history") or {}

            code_risk_ms = code_risk_res.get("duration_ms") or (code_risk_res.get("metadata") or {}).get("code_risk_ms", 0.0)
            repo_ctx_ms = (code_risk_res.get("metadata") or {}).get("repository_context_ms", 0.0)
            infra_risk_ms = infra_risk_res.get("duration_ms") or (infra_risk_res.get("metadata") or {}).get("infra_risk_ms", 0.0)
            incident_history_ms = incident_history_res.get("duration_ms") or (incident_history_res.get("metadata") or {}).get("incident_history_ms", 0.0)

            decision = make_decision(
                correlation_id,
                results,
            )

            aggregation_ms = round(
                (time.perf_counter() - started) * 1000,
                2,
            )

            total_pipeline_ms = round(
                webhook_ms + max(code_risk_ms, infra_risk_ms, incident_history_ms) + aggregation_ms,
                2
            )

            decision.setdefault("metadata", {})
            decision["metadata"]["aggregation_latency_ms"] = aggregation_ms
            decision["metadata"]["timings"] = {
                "webhook_ms": webhook_ms,
                "repository_context_ms": repo_ctx_ms,
                "code_risk_ms": code_risk_ms,
                "infra_risk_ms": infra_risk_ms,
                "incident_history_ms": incident_history_ms,
                "aggregation_ms": aggregation_ms,
                "total_pipeline_ms": total_pipeline_ms
            }

            # Map individual agent states
            agent_states = {}
            for agent_name in self.expected_agents:
                if agent_name in results:
                    res = results[agent_name]
                    if res.get("status") == "TIMED_OUT":
                        agent_states[agent_name] = "TIMED_OUT"
                    elif res.get("confidence", 0) == 0.0 and "error" in (res.get("metadata") or {}):
                        agent_states[agent_name] = "UNHEALTHY"
                    elif (res.get("metadata") or {}).get("waiting_for_dependency"):
                        agent_states[agent_name] = "WAITING_FOR_DEPENDENCY"
                    else:
                        agent_states[agent_name] = "COMPLETED"
                else:
                    agent_states[agent_name] = "TIMED_OUT"

            decision["metadata"]["agent_states"] = agent_states

            self.publisher.publish(
                correlation_id,
                decision,
            )

            self.redis_store.save_final_decision(
                correlation_id,
                decision,
            )

            logger.info(
                f"Aggregation complete for {correlation_id} "
                f"in {aggregation_ms} ms (total pipeline: {total_pipeline_ms} ms). "
                f"Decision: {decision['decision']}"
            )

        except Exception as e:
            logger.error(
                f"Error executing aggregation for "
                f"{correlation_id}: {e}",
                exc_info=True,
            )

        finally:
            self.redis_store.delete_deployment_data(
                correlation_id
            )

    def process_timeouts(self) -> None:
        """Scan Redis for expired deployments and finalize once when AGGREGATION_TIMEOUT_SECONDS expires."""

        now = time.time()

        try:
            for byte_key in self.redis_store.client.scan_iter("timeout:*"):

                key = byte_key.decode("utf-8")
                correlation_id = key.split(":")[-1]

                raw_time = self.redis_store.client.get(key)

                if not raw_time:
                    continue

                start_time = float(raw_time.decode("utf-8"))

                if now - start_time < self.settings.timeout_seconds:
                    continue

                logger.warning(
                    f"[aggregator] Timeout expired ({self.settings.timeout_seconds}s) for {correlation_id}"
                )

                # If already finalized, clean up marker and continue
                if self.redis_store.get_final_decision(correlation_id):
                    self.redis_store.delete_timeout_marker(
                        correlation_id
                    )
                    continue

                results = self.redis_store.get_agent_results(
                    correlation_id
                )

                missing = (
                    self.expected_agents
                    - set(results.keys())
                )

                logger.warning(
                    f"Timeout aggregation triggered for "
                    f"{correlation_id}. "
                    f"Missing agents: {missing}"
                )

                # Add placeholders for missing agents marked TIMED_OUT
                for agent_name in missing:
                    results[agent_name] = {
                        "agent": agent_name,
                        "correlation_id": correlation_id,
                        "score": 0,
                        "severity": "low",
                        "confidence": 0.0,
                        "status": "TIMED_OUT",
                        "reasons": [f"Agent '{agent_name}' did not respond within {self.settings.timeout_seconds}s timeout."],
                        "recommendations": [],
                        "metadata": {"status": "TIMED_OUT"}
                    }

                if results:
                    self._aggregate_and_publish(
                        correlation_id,
                        results,
                    )
                else:
                    self.redis_store.delete_deployment_data(
                        correlation_id
                    )

        except Exception as e:
            logger.error(
                f"Error in timeout watcher: {e}",
                exc_info=True,
            )