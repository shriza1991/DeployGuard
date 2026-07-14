import time
from typing import Any, Dict, Set

from redis_store import RedisStore
from kafka_producer import RiskDecisionPublisher
from decision_engine import make_decision
from logger import logger
from config import Settings


class AggregationEngine:
    EXPECTED_AGENTS: Set[str] = {
        "code-risk",
        "infra-risk",
        "incident-history",
    }

    def __init__(
        self,
        settings: Settings,
        redis_store: RedisStore,
        publisher: RiskDecisionPublisher,
    ):
        self.settings = settings
        self.redis_store = redis_store
        self.publisher = publisher

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

        if agent_name not in self.EXPECTED_AGENTS:
            logger.warning(
                f"Received result from unexpected agent '{agent_name}': {payload}"
            )
            return

        # Ignore late agent results if a final decision already exists
        if self.redis_store.get_final_decision(correlation_id):
            logger.info(
                f"Ignoring late result from '{agent_name}' "
                f"for completed deployment {correlation_id}"
            )
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
            f"Current results for {correlation_id}: {current_agents}"
        )

        # Aggregate immediately if everyone has responded
        if current_agents == self.EXPECTED_AGENTS:
            logger.info(
                f"All expected agents responded for "
                f"{correlation_id}. Triggering immediate aggregation."
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

        # Atomic lock
        if not self.redis_store.delete_timeout_marker(correlation_id):
            logger.info(
                f"Aggregation already handled for {correlation_id}"
            )
            return

        try:
            started = time.perf_counter()

            decision = make_decision(
                correlation_id,
                results,
            )

            latency_ms = round(
                (time.perf_counter() - started) * 1000,
                2,
            )

            decision.setdefault("metadata", {})
            decision["metadata"]["aggregation_latency_ms"] = latency_ms

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
                f"in {latency_ms} ms. "
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
        """Scan Redis for expired deployments."""

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
                    f"Timeout expired for {correlation_id}"
                )

                # If already finalized, ignore
                if self.redis_store.get_final_decision(correlation_id):
                    self.redis_store.delete_timeout_marker(
                        correlation_id
                    )
                    continue

                results = self.redis_store.get_agent_results(
                    correlation_id
                )

                missing = (
                    self.EXPECTED_AGENTS
                    - set(results.keys())
                )

                logger.warning(
                    f"Timeout aggregation triggered for "
                    f"{correlation_id}. "
                    f"Missing agents: {missing}"
                )

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