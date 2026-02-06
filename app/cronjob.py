from __future__ import annotations

import json
import logging
import os
from datetime import UTC, datetime

from redis import Redis

REDIS_HOST = os.getenv("REDIS_HOST", "redis")
REDIS_PORT = os.getenv("REDIS_PORT", "6379")
REDIS_PASSWORD = os.getenv("REDIS_PASSWORD", "")
QUEUE_NAME = os.getenv("QUEUE_NAME", "task_queue")
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

logging.basicConfig(
    level=getattr(logging, LOG_LEVEL.upper(), logging.INFO),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("cronjob")


def get_redis() -> Redis[str]:
    return Redis(
        host=REDIS_HOST,
        port=int(REDIS_PORT),
        password=REDIS_PASSWORD or None,
        decode_responses=True,
    )


def main() -> None:
    timestamp = datetime.now(UTC).isoformat()
    logger.info("Starting at %s", timestamp)

    r = get_redis()

    stats = {
        "timestamp": timestamp,
        "tasks_created": int(r.get("stats:tasks_created") or 0),
        "tasks_processed": int(r.get("stats:tasks_processed") or 0),
        "tasks_failed": int(r.get("stats:tasks_failed") or 0),
        "queue_length": r.llen(QUEUE_NAME),
    }

    logger.info("Current stats: %s", json.dumps(stats))

    r.lpush("stats:history", json.dumps(stats))
    r.ltrim("stats:history", 0, 99)

    r.set("stats:last_cron_run", timestamp)

    if stats["queue_length"] > 100:
        logger.warning("Queue length is %d, consider scaling workers!", stats["queue_length"])

    if stats["tasks_created"] > 0:
        success_rate = (stats["tasks_processed"] / stats["tasks_created"]) * 100
        logger.info("Success rate: %.1f%%", success_rate)

    logger.info("Completed successfully")


if __name__ == "__main__":
    main()
