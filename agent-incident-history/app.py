from __future__ import annotations

import logging
from functools import lru_cache
from typing import Any

from incident_history.config import get_settings
from incident_history.consumer import DeploymentEventConsumer
from incident_history.health import start_health_server
from incident_history.publisher import RiskResultPublisher
from incident_history.service import create_service

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("incident-history-agent")


@lru_cache(maxsize=1)
def get_service():
    return create_service(get_settings())


def analyze_incident_history(payload: dict[str, Any]) -> dict[str, Any]:
    """Compatibility helper for tests and local smoke checks."""
    result = get_service().analyze_event(payload, correlation_id=None)
    return {
        key: value
        for key, value in result.items()
        if key not in {"agent", "correlation_id"}
    }


def main() -> None:
    settings = get_settings()
    service = get_service()
    start_health_server(service, settings.health_host, settings.health_port)
    publisher = RiskResultPublisher(settings.kafka_broker, settings.output_topic)
    consumer = DeploymentEventConsumer(settings, service, publisher)
    consumer.run_forever()


if __name__ == "__main__":
    main()

