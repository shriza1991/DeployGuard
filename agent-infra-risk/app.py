import json
import os
import time

from kafka import KafkaConsumer, KafkaProducer

KAFKA_BROKER = os.getenv("KAFKA_BROKER", "kafka:9092")
INPUT_TOPIC = "deployment-events"
OUTPUT_TOPIC = "risk-results"
GROUP_ID = "agent-infra-risk-group"
SEVERE_WINDOW = {"00": 15, "01": 15, "02": 15, "03": 15, "04": 10, "05": 10, "06": 5, "07": 5, "08": 5, "09": 5, "10": 5, "11": 5, "12": 5, "13": 5, "14": 5, "15": 10, "16": 15, "17": 20, "18": 25, "19": 30, "20": 35, "21": 40, "22": 45, "23": 50}

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


def clamp(value: float, minimum: float = 0, maximum: float = 100) -> int:
    return int(max(minimum, min(maximum, value)))


def score_infra_risk(payload: dict) -> dict:
    deployment_time = payload.get("deployment_time")
    if not deployment_time:
        now_hour = time.strftime("%H")
    else:
        try:
            now_hour = deployment_time[:2]
        except Exception:
            now_hour = time.strftime("%H")

    window_risk = SEVERE_WINDOW.get(now_hour, 20)
    simulated_cpu = float(os.getenv("SIMULATED_CPU", "0.55"))
    simulated_error_rate = float(os.getenv("SIMULATED_ERROR_RATE", "0.02"))
    simulated_latency = float(os.getenv("SIMULATED_LATENCY", "120"))

    risk = 20
    risk += simulated_cpu * 50
    risk += min(20, simulated_error_rate * 1000)
    risk += min(20, (simulated_latency - 100) / 5)
    risk += window_risk * 0.5

    if payload.get("environment") == "production":
        risk += 10
    if payload.get("hotfix"):
        risk += 15

    score = clamp(risk)
    return {
        "score": score,
        "details": {
            "deployment_hour": now_hour,
            "window_risk": window_risk,
            "simulated_cpu": simulated_cpu,
            "simulated_error_rate": simulated_error_rate,
            "simulated_latency_ms": simulated_latency,
            "environment": payload.get("environment", "unknown"),
            "hotfix": bool(payload.get("hotfix", False)),
        },
    }


print("agent-infra-risk started, waiting for events...")
for msg in consumer:
    event = msg.value
    payload = event.get("payload", {})
    correlation_id = event.get("correlation_id")
    print("[infra-risk] received event", event)

    score_data = score_infra_risk(payload)
    output = {
        "agent": "infra-risk",
        "score": score_data["score"],
        "correlation_id": correlation_id,
        "details": score_data["details"],
    }
    producer.send(OUTPUT_TOPIC, output)
    producer.flush()
    print("[infra-risk] published result", output)
    time.sleep(1)
