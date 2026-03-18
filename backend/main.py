import asyncio
import uvicorn
from contextlib import asynccontextmanager
from dotenv import load_dotenv
from fastapi import FastAPI
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from routers.sync import router, run_sync
import os

load_dotenv()

SYNC_INTERVAL_MINUTES = int(os.getenv("SYNC_INTERVAL_MINUTES", "15"))


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Run an immediate sync on startup, then schedule recurring syncs.
    print(f"[Scheduler] Running initial sync on startup...")
    await run_sync()

    scheduler = AsyncIOScheduler()
    scheduler.add_job(
        run_sync,
        trigger="interval",
        minutes=SYNC_INTERVAL_MINUTES,
        id="sync_job",
        replace_existing=True,
    )
    scheduler.start()
    print(f"[Scheduler] Polling every {SYNC_INTERVAL_MINUTES} minute(s).")

    yield  # server runs here

    scheduler.shutdown()
    print("[Scheduler] Shut down.")


app = FastAPI(lifespan=lifespan)

app.include_router(router)


@app.get("/")
async def read_root():
    return {
        "status": "ok",
        "sync_interval_minutes": SYNC_INTERVAL_MINUTES,
    }


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
