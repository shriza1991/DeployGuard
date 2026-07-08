import time
from typing import Any, Dict, Set
from redis_store import RedisStore
from kafka_producer import RiskDecisionPublisher
from decision_engine import make_decision
from logger import logger
from config import Settings

class AggregationEngine:
    EXPECTED_AGENTS: Set[str] = {"code-risk", "infra-risk", "incident-history"}

    def __init__(self, settings: Settings, redis_store: RedisStore, publisher: RiskDecisionPublisher):
        self.settings = settings
        self.redis_store = redis_store
        self.publisher = publisher

    def handle_agent_result(self, correlation_id: str, agent_name: str, payload: Dict[str, Any]) -> None:
        if not correlation_id:
            logger.warning(f"Received result with missing correlation_id: {payload}")
            return

        if agent_name not in self.EXPECTED_AGENTS:
            logger.warning(f"Received result from unexpected agent '{agent_name}': {payload}")
            return

        # 1. Save agent result to Redis
        self.redis_store.save_agent_result(correlation_id, agent_name, payload)

        # 2. Start timeout timer if this is the first agent result
        now = time.time()
        self.redis_store.set_timeout_marker(correlation_id, now)

        # 3. Retrieve all results currently accumulated
        results = self.redis_store.get_agent_results(correlation_id)
        current_agents = set(results.keys())
        
        logger.info(f"Current results for {correlation_id}: {current_agents}")

        # 4. If all expected agents have reported, aggregate and publish
        if current_agents == self.EXPECTED_AGENTS:
            logger.info(f"All expected agents responded for {correlation_id}. Triggering immediate aggregation.")
            self._aggregate_and_publish(correlation_id, results)

    def _aggregate_and_publish(self, correlation_id: str, results: Dict[str, Dict[str, Any]]) -> None:
        # Atomic lock check using delete_timeout_marker. If it returns True, we won the race to aggregate.
        if self.redis_store.delete_timeout_marker(correlation_id):
            try:
                started = time.perf_counter()
                decision = make_decision(correlation_id, results)
                latency_ms = round((time.perf_counter() - started) * 1000, 2)
                
                # Add latency to final decision metadata
                if "metadata" not in decision:
                    decision["metadata"] = {}
                decision["metadata"]["aggregation_latency_ms"] = latency_ms

                # Publish to Kafka
                self.publisher.publish(correlation_id, decision)

                # Save final decision to Redis for GET /decision REST API queries
                self.redis_store.save_final_decision(correlation_id, decision)

                logger.info(f"Aggregation complete for correlation_id {correlation_id} in {latency_ms}ms. Decision: {decision['decision']}")
            except Exception as e:
                logger.error(f"Error executing aggregation for {correlation_id}: {e}", exc_info=True)
            finally:
                # Always clean up temp results
                self.redis_store.delete_deployment_data(correlation_id)
        else:
            logger.info(f"Aggregation already handled by another thread for correlation_id {correlation_id}")

    def process_timeouts(self) -> None:
        """Scan Redis for timeouts and process any expired deployments."""
        now = time.time()
        
        # Scan for all timeout keys
        # The scan_iter function scans keys matching timeout:*
        try:
            for byte_key in self.redis_store.client.scan_iter("timeout:*"):
                key = byte_key.decode("utf-8")
                correlation_id = key.split(":")[-1]
                
                raw_time = self.redis_store.client.get(key)
                if not raw_time:
                    continue
                    
                start_time = float(raw_time.decode("utf-8"))
                elapsed = now - start_time
                
                if elapsed >= self.settings.timeout_seconds:
                    logger.warning(f"Timeout expired ({elapsed:.1f}s >= {self.settings.timeout_seconds}s) for {correlation_id}")
                    # Fetch whatever results we have and process them
                    results = self.redis_store.get_agent_results(correlation_id)
                    
                    missing = self.EXPECTED_AGENTS - set(results.keys())
                    logger.warning(f"Timeout aggregation triggered for {correlation_id}. Missing agents: {missing}")
                    
                    if results:
                        self._aggregate_and_publish(correlation_id, results)
                    else:
                        # Clean up if somehow there are no results
                        logger.warning(f"No results found for expired correlation_id {correlation_id}, cleaning up.")
                        self.redis_store.delete_deployment_data(correlation_id)
        except Exception as e:
            logger.error(f"Error in timeout watcher: {e}", exc_info=True)
