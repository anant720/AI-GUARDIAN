import uvicorn
import multiprocessing
import os

if __name__ == "__main__":
    # In production, we use multiple workers to handle concurrent scans (2-4 as requested)
    # CPU count * 2 is a common heuristic, but for LLM gating, we target 4 workers.
    workers = int(os.getenv("WEB_CONCURRENCY", 4))
    
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=int(os.getenv("PORT", 8000)),
        workers=workers,
        loop="uvloop",
        http="h11",
        log_level="info"
    )
