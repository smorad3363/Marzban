from app import app, logger, scheduler
from app.device_limit.engine import engine


@app.on_event("startup")
def start_device_limit_engine():
    engine.start()
    logger.info("Native device-limit log collectors started")


@app.on_event("shutdown")
def stop_device_limit_engine():
    engine.stop()


scheduler.add_job(
    engine.evaluate,
    "interval",
    seconds=10,
    coalesce=True,
    max_instances=1,
)
scheduler.add_job(
    engine.retention_cleanup,
    "interval",
    hours=24,
    coalesce=True,
    max_instances=1,
)
