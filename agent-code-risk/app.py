import datetime
import json
import logging
import os
import time
from http.server import BaseHTTPRequestHandler, HTTPServer
import threading

from kafka import KafkaConsumer, KafkaProducer

from pipeline import run_analysis_pipeline

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

# Pipeline replaces the old two-step analyze_code_risk + LLMReasoner flow.
# run_analysis_pipeline() runs Phase 1 (deterministic) then Phase 2 (LLM review)
# and returns an aggregator-compatible dict.

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

def calculate_agent_confidence(payload: dict, analysis: dict, llm_result: dict | None = None, timed_out: bool = False) -> tuple[float, list[str]]:
    factors: list[str] = list(analysis.get("confidence_factors") or [])
    conf = 0.0

    analyzer_conf = analysis.get("confidence")
    if analyzer_conf is not None and isinstance(analyzer_conf, (int, float)) and analyzer_conf > 0:
        val = float(analyzer_conf)
        conf = val / 100.0 if val > 1.0 else val

    llm_conf = (llm_result or {}).get("confidence", 0.0)
    llm_available = (llm_result or {}).get("available", False)
    if llm_available and isinstance(llm_conf, (int, float)) and llm_conf > 0:
        llm_val = float(llm_conf)
        llm_val = llm_val / 100.0 if llm_val > 1.0 else llm_val
        conf = max(conf, llm_val)
        factors.append("LLM verification completed")
    elif llm_available:
        factors.append("LLM reasoning active")

    if conf == 0.0:
        base = 50
        patch_text = payload.get("patch_text") or payload.get("diff") or ""
        files = payload.get("changed_files") or payload.get("files") or []
        if patch_text.strip() or files:
            base += 20
            factors.append("Git diff available")
        else:
            base -= 20

        pr = payload.get("pull_request") or {}
        if pr.get("title") or pr.get("body") or (payload.get("head_commit") or {}).get("message"):
            base += 15
            factors.append("PR metadata available")
        else:
            base -= 15

        if analysis.get("reasons") or analysis.get("deterministic_findings"):
            base += 10
            factors.append("Deterministic findings matched")

        if llm_available:
            base += 10

        if (payload.get("repository") or {}).get("name"):
            base += 5
            factors.append("Repository metadata parsed")

        if timed_out:
            base -= 20

        conf = max(0.0, min(100.0, float(base))) / 100.0

    seen = set()
    dedup_factors = []
    for f in factors:
        if f not in seen:
            seen.add(f)
            dedup_factors.append(f)

    return round(max(0.0, min(1.0, conf)), 2), dedup_factors


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

    start_time_sec = time.time()
    started_at_iso = datetime.datetime.fromtimestamp(start_time_sec, datetime.timezone.utc).isoformat()
    start_run = time.perf_counter()
    confidence_val = 0.0
    try:
        # ── Two-phase pipeline ─────────────────────────────────────────────────
        # Phase 1: deterministic analysis (diff parser + language classifiers + detectors)
        # Phase 2: LLM review (Gemini receives AnalysisReport, never raw payload)
        pipeline_result = run_analysis_pipeline(payload)

        confidence_val, confidence_factors = calculate_agent_confidence(
            payload,
            pipeline_result,         # pipeline_result has same keys as old 'analysis'
            {                        # synthetic llm_result for backward-compat scorer
                "confidence": (pipeline_result.get("llm") or {}).get("confidence", 0.0),
                "available": (pipeline_result.get("llm") or {}).get("available", False),
            },
        )

        completed_time_sec = time.time()
        completed_at_iso = datetime.datetime.fromtimestamp(completed_time_sec, datetime.timezone.utc).isoformat()
        latency_ms = round((time.perf_counter() - start_run) * 1000.0, 2)

        repo_metrics = pipeline_result.get("metadata", {}).get("repository_evidence_metrics") or {}
        repo_ctx_ms = repo_metrics.get("retrieval_latency_ms", 0.0)

        meta = {
            **pipeline_result.get("metadata", {}),
            "confidence_factors": confidence_factors,
            "started_at": started_at_iso,
            "completed_at": completed_at_iso,
            "code_risk_ms": latency_ms,
            "repository_context_ms": repo_ctx_ms,
        }

        llm_block = pipeline_result.get("llm") or {}

        output = {
            "agent": "code-risk",
            "correlation_id": correlation_id,
            "score": pipeline_result["score"],
            "severity": pipeline_result["severity"],
            "confidence": confidence_val,
            "confidence_factors": confidence_factors,
            "reasons": pipeline_result["reasons"],
            "recommendations": pipeline_result["recommendations"],
            "started_at": started_at_iso,
            "completed_at": completed_at_iso,
            "duration_ms": latency_ms,
            "metadata": meta,
            "llm": {
                "provider": llm_block.get("provider"),
                "available": llm_block.get("available", False),
                "summary": llm_block.get("summary"),
                "risk_reasoning": llm_block.get("risk_reasoning", []),
                "recommendations": llm_block.get("recommendations", []),
                "confidence": llm_block.get("confidence", 0.0),
            },
            # Additive Phase 2 fields (ignored by current aggregator, available for frontend)
            "deployment_decision": pipeline_result.get("deployment_decision", "REVIEW"),
            "finding_analyses": pipeline_result.get("finding_analyses", []),
            "ai_observations": pipeline_result.get("ai_observations", []),
            "confidence_rationale": pipeline_result.get("confidence_rationale", ""),
        }
        producer.send(OUTPUT_TOPIC, output)
        producer.flush()
        logger.info("[code-risk] published result %s", output)
    except Exception as exc:  # pragma: no cover - defensive logging
        logger.exception("[code-risk] failed to analyze event: %s", exc)
        completed_at_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()
        latency_ms = round((time.perf_counter() - start_run) * 1000.0, 2)
        output = {
            "agent": "code-risk",
            "correlation_id": correlation_id,
            "score": 0,
            "severity": "low",
            "confidence": 0.0,
            "reasons": ["Unexpected failure while analyzing the deployment change."],
            "recommendations": ["Inspect the service logs and retry the analysis."],
            "started_at": started_at_iso,
            "completed_at": completed_at_iso,
            "duration_ms": latency_ms,
            "metadata": {"error": str(exc), "payload_type": type(event).__name__, "started_at": started_at_iso, "completed_at": completed_at_iso, "code_risk_ms": latency_ms},
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

