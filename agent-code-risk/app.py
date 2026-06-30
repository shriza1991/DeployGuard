import json
import os
import re
import time

import requests
from kafka import KafkaConsumer, KafkaProducer

KAFKA_BROKER = os.getenv("KAFKA_BROKER", "kafka:9092")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
INPUT_TOPIC = "deployment-events"
OUTPUT_TOPIC = "risk-results"
GROUP_ID = "agent-code-risk-group"

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

SECURITY_KEYWORDS = ["auth", "crypto", "vulnerability", "privilege", "security", "secret", "token"]
CRITICAL_EXTENSIONS = {"py", "js", "ts", "go", "java", "yaml", "yml", "tf", "sh"}


def clamp(value: float, minimum: float = 0, maximum: float = 100) -> int:
    return int(max(minimum, min(maximum, value)))


def fetch_pull_request_files(pr_url: str) -> list[dict]:
    if not GITHUB_TOKEN or not pr_url:
        return []

    headers = {"Authorization": f"token {GITHUB_TOKEN}", "Accept": "application/vnd.github.v3+json"}
    files_url = pr_url.rstrip("/") + "/files"
    response = requests.get(files_url, headers=headers, timeout=10)
    if response.status_code != 200:
        return []
    return response.json()


def count_critical_files(file_list: list[dict]) -> int:
    count = 0
    for item in file_list:
        path = item.get("filename", "")
        ext = path.split(".")[-1].lower()
        if ext in CRITICAL_EXTENSIONS:
            count += 1
    return count


def score_code_risk(payload: dict) -> dict:
    pr = payload.get("pull_request") or {}
    head_commit = payload.get("head_commit") or {}

    changed_files = pr.get("changed_files", 0)
    additions = pr.get("additions", 0)
    deletions = pr.get("deletions", 0)
    title = str(pr.get("title", ""))
    body = str(pr.get("body", ""))
    message = str(head_commit.get("message", ""))

    text = " ".join([title, body, message]).lower()
    keyword_hits = sum(1 for token in SECURITY_KEYWORDS if token in text)
    extra_risk = 10 * keyword_hits

    file_list = fetch_pull_request_files(pr.get("url", ""))
    critical_count = count_critical_files(file_list)
    critical_bonus = critical_count * 5

    if changed_files > 0:
        score = 20 + changed_files * 3 + additions * 0.4 + deletions * 0.4 + extra_risk + critical_bonus
    else:
        score = 35 + extra_risk

    if text:
        score += min(15, len(re.findall(r"\b(issue|fix|hotfix|security|inject|vuln)\b", text)) * 5)

    return {
        "score": clamp(score),
        "details": {
            "changed_files": changed_files,
            "additions": additions,
            "deletions": deletions,
            "keyword_hits": keyword_hits,
            "critical_files": critical_count,
            "source": "pull_request" if pr else "commit",
        },
    }


print("agent-code-risk started, waiting for events...")
for msg in consumer:
    event = msg.value
    payload = event.get("payload", {})
    correlation_id = event.get("correlation_id")
    print("[code-risk] received event", event)

    score_data = score_code_risk(payload)
    output = {
        "agent": "code-risk",
        "score": score_data["score"],
        "correlation_id": correlation_id,
        "details": score_data["details"],
    }
    producer.send(OUTPUT_TOPIC, output)
    producer.flush()
    print("[code-risk] published result", output)
    time.sleep(1)
