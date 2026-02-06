from __future__ import annotations

import json
import logging
import os
import uuid
from datetime import UTC, datetime

from flask import Flask, jsonify, request
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Gauge, generate_latest
from redis import Redis

REDIS_HOST = os.getenv("REDIS_HOST", "redis")
REDIS_PORT = os.getenv("REDIS_PORT", "6379")
REDIS_PASSWORD = os.getenv("REDIS_PASSWORD", "")
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
QUEUE_NAME = os.getenv("QUEUE_NAME", "task_queue")

logging.basicConfig(
    level=getattr(logging, LOG_LEVEL.upper(), logging.INFO),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("api")

app = Flask(__name__)

TASKS_CREATED = Counter("tasks_created_total", "Total tasks created")
TASKS_IN_QUEUE = Gauge("tasks_in_queue", "Current tasks in queue")
REQUEST_COUNT = Counter("http_requests_total", "Total HTTP requests", ["method", "endpoint"])


def get_redis() -> Redis[str]:
    return Redis(
        host=REDIS_HOST,
        port=int(REDIS_PORT),
        password=REDIS_PASSWORD or None,
        decode_responses=True,
    )


@app.route("/health")
def health():
    REQUEST_COUNT.labels(method="GET", endpoint="/health").inc()
    return jsonify({"status": "healthy", "timestamp": datetime.now(UTC).isoformat()})


@app.route("/ready")
def ready():
    REQUEST_COUNT.labels(method="GET", endpoint="/ready").inc()
    try:
        r = get_redis()
        r.ping()
        return jsonify({"status": "ready"})
    except Exception as e:
        logger.warning("Readiness check failed: %s", e)
        return jsonify({"status": "not ready", "error": str(e)}), 503


@app.route("/tasks", methods=["POST"])
def create_task():
    REQUEST_COUNT.labels(method="POST", endpoint="/tasks").inc()
    data = request.get_json() or {}

    task = {
        "id": str(uuid.uuid4()),
        "payload": data.get("payload", "default task"),
        "created_at": datetime.now(UTC).isoformat(),
        "status": "pending",
    }

    r = get_redis()
    r.lpush(QUEUE_NAME, json.dumps(task))
    r.incr("stats:tasks_created")

    TASKS_CREATED.inc()
    TASKS_IN_QUEUE.set(r.llen(QUEUE_NAME))

    logger.info("Task created: %s", task["id"])
    return jsonify({"message": "Task created", "task": task}), 201


@app.route("/tasks", methods=["GET"])
def list_tasks():
    REQUEST_COUNT.labels(method="GET", endpoint="/tasks").inc()
    r = get_redis()
    tasks = r.lrange(QUEUE_NAME, 0, 9)
    queue_len = r.llen(QUEUE_NAME)

    TASKS_IN_QUEUE.set(queue_len)

    return jsonify(
        {
            "pending_tasks": [json.loads(t) for t in tasks],
            "queue_length": queue_len,
        }
    )


@app.route("/stats")
def stats():
    REQUEST_COUNT.labels(method="GET", endpoint="/stats").inc()
    r = get_redis()
    return jsonify(
        {
            "tasks_created": int(r.get("stats:tasks_created") or 0),
            "tasks_processed": int(r.get("stats:tasks_processed") or 0),
            "tasks_failed": int(r.get("stats:tasks_failed") or 0),
            "last_cron_run": r.get("stats:last_cron_run"),
            "queue_name": QUEUE_NAME,
            "log_level": LOG_LEVEL,
            "pod_name": os.getenv("POD_NAME", "unknown"),
        }
    )


@app.route("/metrics")
def metrics():
    r = get_redis()
    try:
        TASKS_IN_QUEUE.set(r.llen(QUEUE_NAME))
    except Exception:
        pass
    return generate_latest(), 200, {"Content-Type": CONTENT_TYPE_LATEST}


if __name__ == "__main__":
    logger.info("Starting API server on port 8080")
    app.run(host="0.0.0.0", port=8080)
