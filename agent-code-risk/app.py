import datetime
import json
import logging
import os
import time
from http.server import BaseHTTPRequestHandler, HTTPServer
import threading

from kafka import KafkaConsumer, KafkaProducer

from llm_reasoner import LLMReasoner
from risk_analyzers import analyze_code_risk

KAFKA_BROKER = os.getenv("KAFKA_BROKER", "kafka:9092")
INPUT_TOPIC = "deployment-events"
OUTPUT_TOPIC = "risk-results"
GROUP_ID = "agent-code-risk-group"

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("code-risk-agent")

producer = KafkaProducer(
    bootstrap_servers=[KAFKA_BROKER],
    value_serializer=lambda value: json.dumps(value).encode("utf-8"),
)

consumer = KafkaConsumer(
    INPUT_TOPIC,
    bootstrap_servers=[KAFKA_BROKER],
    group_id=GROUP_ID,
    auto_offset_reset="earliest",
    value_deserializer=lambda m: json.loads(m.decode("utf-8")),
)

reasoner = LLMReasoner()

# Stats tracking
STATS = {
    "start_time": time.time(),
    "analysis_count": 0,
    "last_run_timestamp": None,
    "total_latency_ms": 0.0,
    "total_confidence": 0.0,
    "version": "1.0.0",
}

class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/health":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            
            uptime = time.time() - STATS["start_time"]
            avg_latency = (STATS["total_latency_ms"] / STATS["analysis_count"]) if STATS["analysis_count"] > 0 else 0.0
            avg_confidence = (STATS["total_confidence"] / STATS["analysis_count"]) if STATS["analysis_count"] > 0 else 0.0
            
            mem_mb = None
            try:
                import resource
                mem_mb = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024.0
            except Exception:
                pass
            
            response = {
                "status": "ok",
                "agent": "code-risk",
                "version": STATS["version"],
                "uptime": uptime,
                "analysis_count": STATS["analysis_count"],
                "last_run_timestamp": STATS["last_run_timestamp"],
                "average_latency_ms": avg_latency,
                "average_confidence": avg_confidence,
                "cpu_usage": None,
                "memory_usage": mem_mb
            }
            self.wfile.write(json.dumps(response).encode("utf-8"))
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, format, *args):
        pass

def start_health_server(port: int = 8081):
    def run():
        server = HTTPServer(("0.0.0.0", port), HealthHandler)
        server.serve_forever()
    t = threading.Thread(target=run, daemon=True)
    t.start()

start_health_server(8081)
logger.info("Health server started on port 8081")

logger.info("agent-code-risk started, waiting for events...")
for msg in consumer:
    event = msg.value
    payload = event.get("payload", {}) if isinstance(event, dict) else {}
    
    logger.info("=" * 80)
    logger.info("CODE RISK PAYLOAD")
    logger.info(json.dumps(payload, indent=2))
    logger.info("=" * 80)
    correlation_id = event.get("correlation_id") if isinstance(event, dict) else None
    logger.info("[code-risk] received event %s", correlation_id)

    start_run = time.perf_counter()
    confidence_val = 0.0
    try:
        analysis = analyze_code_risk(payload)
        llm_result = reasoner.reason_about_change(payload, analysis)
        confidence_val = max(0.0, min(1.0, analysis.get("confidence", 0.0) / 100.0))

        output = {
            "agent": "code-risk",
            "correlation_id": correlation_id,
            "score": analysis["score"],
            "severity": analysis["severity"],
            "confidence": confidence_val,
            "reasons": analysis["reasons"],
            "recommendations": analysis["recommendations"],
            "metadata": analysis["metadata"],
            "llm": {
                "provider": llm_result.get("provider"),
                "available": llm_result.get("available", False),
                "summary": llm_result.get("summary"),
                "risk_reasoning": llm_result.get("risk_reasoning", []),
                "recommendations": llm_result.get("recommendations", []),
                "confidence": llm_result.get("confidence", 0.0),
            },
        }
        producer.send(OUTPUT_TOPIC, output)
        producer.flush()
        logger.info("[code-risk] published result %s", output)
    except Exception as exc:  # pragma: no cover - defensive logging
        logger.exception("[code-risk] failed to analyze event: %s", exc)
        output = {
            "agent": "code-risk",
            "correlation_id": correlation_id,
            "score": 0,
            "severity": "low",
            "confidence": 0.0,
            "reasons": ["Unexpected failure while analyzing the deployment change."],
            "recommendations": ["Inspect the service logs and retry the analysis."],
            "metadata": {"error": str(exc), "payload_type": type(event).__name__},
            "llm": {
                "summary": "Deterministic analysis was not completed due to an unexpected error.",
                "additional_risks": [],
                "deployment_recommendation": "Do not rely on the automated result until the service is healthy.",
                "reasoning": "The agent encountered an unexpected processing error.",
                "provider": "unavailable",
                "available": False,
            },
        }
        producer.send(OUTPUT_TOPIC, output)
        producer.flush()
    finally:
        latency_ms = (time.perf_counter() - start_run) * 1000.0
        STATS["analysis_count"] += 1
        STATS["last_run_timestamp"] = datetime.datetime.utcnow().isoformat() + "Z"
        STATS["total_latency_ms"] += latency_ms
        STATS["total_confidence"] += confidence_val

    time.sleep(1)

