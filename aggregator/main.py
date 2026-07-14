import threading
import time
from fastapi import FastAPI
from api import router
from config import get_settings
from redis_store import RedisStore
from kafka_producer import RiskDecisionPublisher
from aggregation_engine import AggregationEngine
from kafka_consumer import RiskResultConsumer
from logger import logger

app = FastAPI(title="DeployGuard Aggregator Service")
app.include_router(router)

settings = get_settings()

redis_store = None
publisher = None
engine = None
consumer = None

def timeout_loop():
    logger.info("Timeout loop watcher started")
    while True:
        try:
            engine.process_timeouts()
        except Exception as e:
            logger.error(f"Error in timeout loop: {e}")
        time.sleep(1.0)

@app.on_event("startup")
def startup_event():
    print("========== STARTUP ==========")
    logger.info("Aggregator startup reached.")