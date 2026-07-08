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
redis_store = RedisStore(settings)
publisher = RiskDecisionPublisher(settings)
engine = AggregationEngine(settings, redis_store, publisher)
consumer = RiskResultConsumer(settings, engine)

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
    # Start consumer thread
    consumer_thread = threading.Thread(target=consumer.run_forever, daemon=True)
    consumer_thread.start()
    logger.info("Started background Kafka consumer thread")

    # Start timeout loop thread
    timeout_thread = threading.Thread(target=timeout_loop, daemon=True)
    timeout_thread.start()
    logger.info("Started background timeout loop thread")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host=settings.api_host, port=settings.api_port, reload=False)
