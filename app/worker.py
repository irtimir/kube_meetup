import json
import logging
import os
import random
import signal
import sys
import time
from typing import Any

from redis import ConnectionError as RedisConnectionError
from redis import Redis

REDIS_HOST = os.getenv("REDIS_HOST", "redis")
REDIS_PORT = os.getenv("REDIS_PORT", "6379")
REDIS_PASSWORD = os.getenv("REDIS_PASSWORD", "")
QUEUE_NAME = os.getenv("QUEUE_NAME", "task_queue")
MAX_RETRIES = int(os.getenv("MAX_RETRIES", "3"))
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
WORKER_ID = os.getenv("POD_NAME", f"worker-{random.randint(1000, 9999)}")

logging.basicConfig(
    level=getattr(logging, LOG_LEVEL.upper(), logging.INFO),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(f"worker.{WORKER_ID}")

running = True


def signal_handler(signum: int, frame: Any) -> None:
    global running
    logger.warning("Received signal %d, initiating graceful shutdown...", signum)
    running = False


def get_redis() -> Redis[str]:
    return Redis(
        host=REDIS_HOST,
        port=int(REDIS_PORT),
        password=REDIS_PASSWORD or None,
        decode_responses=True,
    )


def process_task(task_data: str) -> dict[str, Any]:
    task = json.loads(task_data)
    logger.info("Processing task %s: %s", task["id"], task["payload"])

    processing_time = random.uniform(1, 3)
    time.sleep(processing_time)

    if random.random() < 0.1:
        raise Exception("Random processing failure (simulated)")

    logger.info("Completed task %s in %.2fs", task["id"], processing_time)
    return task


def main() -> None:
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)

    logger.info("Worker starting, connecting to Redis at %s:%s", REDIS_HOST, REDIS_PORT)
    logger.info("Queue: %s, Max retries: %d", QUEUE_NAME, MAX_RETRIES)

    r = get_redis()

    while running:
        try:
            r.ping()
            break
        except RedisConnectionError:
            logger.warning("Waiting for Redis...")
            time.sleep(2)

    logger.info("Connected to Redis, starting to process tasks")

    while running:
        try:
            result = r.brpop([QUEUE_NAME], timeout=5)

            if result is None:
                logger.debug("No tasks in queue, waiting...")
                continue

            _, task_data = result

            try:
                process_task(task_data)
                r.incr("stats:tasks_processed")
            except Exception as e:
                logger.error("Task failed: %s", e)
                r.incr("stats:tasks_failed")
        except RedisConnectionError:
            logger.error("Lost Redis connection, reconnecting...")
            time.sleep(2)
            r = get_redis()
        except Exception as e:
            logger.exception("Unexpected error: %s", e)
            time.sleep(1)

    logger.info("Worker shutting down gracefully")
    sys.exit(0)


if __name__ == "__main__":
    main()
