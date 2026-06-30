import json
import os
import time

import redis
from kafka import KafkaConsumer, KafkaProducer

KAFKA_BROKER = os.getenv("KAFKA_BROKER", "kafka:9092")
REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")
INPUT_TOPIC = "risk-results"
OUTPUT_TOPIC = "risk-decisions"
GROUP_ID = "aggregator-group"

redis_client = redis.Redis.from_url(REDIS_URL)
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

EXPECTED_AGENTS = {"code-risk", "infra-risk", "incident-history"}
TIMEOUT_SECONDS = 10

def publish_decision(correlation_id: str, status: str):
    redis_key = f"deployguard:results:{correlation_id}"
    metadata_key = f"deployguard:timeout:{correlation_id}"
    results = redis_client.hgetall(redis_key)
    if not results:
        return

    combined = [json.loads(v.decode("utf-8")) for v in results.values()]
    decision = {
        "correlation_id": correlation_id,
        "results": combined,
        "final_score": sum(item["score"] for item in combined) / len(combined),
        "status": status,
    }
    producer.send(OUTPUT_TOPIC, decision)
    producer.flush()
    print(f"[aggregator] published final decision ({status})", decision)
    redis_client.delete(redis_key)
    redis_client.delete(metadata_key)


def timeout_watcher():
    while True:
        for key in redis_client.scan_iter("deployguard:timeout:*"):
            correlation_id = key.decode("utf-8").split(":")[-1]
            created = redis_client.get(key)
            if not created:
                continue
            created_ts = int(created.decode("utf-8"))
            if time.time() - created_ts >= TIMEOUT_SECONDS:
                print(f"[aggregator] timeout reached for {correlation_id}")
                publish_decision(correlation_id, "timeout")
        time.sleep(1)

print("aggregator started, waiting for risk results...")

import threading
threading.Thread(target=timeout_watcher, daemon=True).start()

for msg in consumer:
    data = msg.value
    correlation_id = data.get("correlation_id")
    if not correlation_id:
        print("[aggregator] skipping result without correlation_id", data)
        continue

    redis_key = f"deployguard:results:{correlation_id}"
    metadata_key = f"deployguard:timeout:{correlation_id}"

    redis_client.hset(redis_key, data["agent"], json.dumps(data))
    redis_client.expire(redis_key, TIMEOUT_SECONDS + 5)

    if not redis_client.exists(metadata_key):
        redis_client.set(metadata_key, int(time.time()), ex=TIMEOUT_SECONDS + 5)

    results = redis_client.hgetall(redis_key)
    agents = {k.decode("utf-8") for k in results.keys()}
    print(f"[aggregator] collected {len(agents)} results for {correlation_id}: {agents}")

    if agents == EXPECTED_AGENTS:
        publish_decision(correlation_id, "complete")
    else:
        print(f"[aggregator] waiting for more results for {correlation_id}")
