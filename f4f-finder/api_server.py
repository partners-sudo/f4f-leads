from fastapi import FastAPI, Response, Request, UploadFile, File
from starlette.responses import StreamingResponse
import asyncio
import json
import logging
from io import StringIO
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uuid
from pathlib import Path
import os
from tasks import (
    scrape_linkedin_companies,
    discover_competitors,
    process_shop_csv,
    request_cancel,
    request_pause,
    request_resume,
)


class LinkedinScrapeRequest(BaseModel):
    keyword: str


class CompetitorScrapeRequest(BaseModel):
    brands: list[str]


class CsvScrapeRequest(BaseModel):
    file_path: str
    source: str | None = "csv_upload"


class ScrapeResponse(BaseModel):
    status: str
    result: dict
    logs: str | None = None


class CancelRequest(BaseModel):
    run_id: str


app = FastAPI()

# Directory for uploaded shop list files (CSV/PDF/JSON)
UPLOAD_DIR = Path(__file__).parent / "uploads"
UPLOAD_DIR.mkdir(exist_ok=True)

RUN_TASKS: dict[str, asyncio.Task] = {}

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.options("/scrape/linkedin")
def options_linkedin() -> Response:
    return Response(status_code=200)


@app.post("/scrape/linkedin", response_model=ScrapeResponse)
def scrape_linkedin(payload: LinkedinScrapeRequest):
    """Run LinkedIn scraping synchronously in the API thread.

    We call the Celery task function directly (not .delay() / .apply_async())
    so it behaves like a normal function and uses its internal run_async
    helper to manage the event loop.
    """
    # Capture logs from the 'finder' logger during this request
    log_stream = StringIO()
    handler = logging.StreamHandler(log_stream)
    logger = logging.getLogger("finder")
    logger.addHandler(handler)
    try:
        result = scrape_linkedin_companies(payload.keyword)
        if not isinstance(result, dict):
            result = {"raw_result": result}
    finally:
        logger.removeHandler(handler)
    logs_value = log_stream.getvalue()
    return ScrapeResponse(status="SUCCESS", result=result, logs=logs_value or None)


@app.post("/upload/shop-file")
async def upload_shop_file(file: UploadFile = File(...)):
    """Upload a CSV/PDF/JSON shop list from the client and store it on the server.

    Returns the server-side file path, which can then be passed to /scrape/csv/stream.
    """
    # Restrict allowed file types
    original_name = file.filename or "uploaded_file"
    suffix = Path(original_name).suffix.lower()
    allowed_suffixes = {".pdf", ".csv", ".json"}
    if suffix not in allowed_suffixes:
        return Response(
            status_code=400,
            content=json.dumps({"error": f"Unsupported file type: {suffix}. Allowed: .pdf, .csv, .json"}),
            media_type="application/json",
        )

    # Ensure unique filename to avoid collisions
    safe_name = f"{uuid.uuid4().hex}{suffix}"
    dest_path = UPLOAD_DIR / safe_name

    try:
        with dest_path.open("wb") as f:
            while True:
                chunk = await file.read(1024 * 1024)
                if not chunk:
                    break
                f.write(chunk)
    except Exception as e:
        return Response(
            status_code=500,
            content=json.dumps({"error": f"Failed to save uploaded file: {e}"}),
            media_type="application/json",
        )

    return {"file_path": str(dest_path)}


@app.get("/scrape/competitors/stream")
async def stream_competitors(brands: str, request: Request):
    """SSE stream for competitor discovery. brands is a comma-separated string."""

    brand_list = [b.strip() for b in brands.split(",") if b.strip()]
    queue: asyncio.Queue[str | None] = asyncio.Queue()

    class QueueLogHandler(logging.Handler):  # type: ignore[misc]
        def emit(self, record: logging.LogRecord) -> None:
            try:
                msg = self.format(record)
                queue.put_nowait(msg)
            except Exception:
                pass

    handler = QueueLogHandler()
    handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
    logger = logging.getLogger("finder")
    logger.addHandler(handler)

    run_id = uuid.uuid4().hex

    async def run_task() -> dict:
        loop = asyncio.get_event_loop()

        def _run() -> dict:
            result = discover_competitors(brand_list, run_id=run_id)
            if not isinstance(result, dict):
                return {"raw_result": result}
            return result

        try:
            return await loop.run_in_executor(None, _run)
        finally:
            logger.removeHandler(handler)
            await queue.put(None)

    task = asyncio.create_task(run_task())
    RUN_TASKS[run_id] = task

    async def event_generator():
        try:
            # First send the run_id so the frontend can cancel this run later
            yield f"event: run_id\ndata: {run_id}\n\n"
            while True:
                if await request.is_disconnected():
                    await request_cancel(run_id)
                    task.cancel()
                    break
                item = await queue.get()
                if item is None:
                    break
                yield f"event: log\ndata: {item}\n\n"

            result = await task
            payload = json.dumps(result)
            yield f"event: result\ndata: {payload}\n\n"
        except asyncio.CancelledError:
            # Task was cancelled (for example via the /scrape/competitors/cancel endpoint).
            # Ensure the task is cancelled but stop the stream quietly without raising.
            task.cancel()
            return
        finally:
            RUN_TASKS.pop(run_id, None)

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@app.get("/scrape/linkedin/stream")
async def stream_linkedin(keyword: str, request: Request):
    """Server-Sent Events stream for LinkedIn scraping logs and final result."""

    queue: asyncio.Queue[str | None] = asyncio.Queue()

    class QueueLogHandler(logging.Handler):  # type: ignore[misc]
        def emit(self, record: logging.LogRecord) -> None:
            try:
                msg = self.format(record)
                queue.put_nowait(msg)
            except Exception:
                pass

    handler = QueueLogHandler()
    handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
    logger = logging.getLogger("finder")
    logger.addHandler(handler)

    run_id = uuid.uuid4().hex

    async def run_task() -> dict:
        loop = asyncio.get_event_loop()

        def _run() -> dict:
            result = scrape_linkedin_companies(keyword, run_id=run_id)
            if not isinstance(result, dict):
                return {"raw_result": result}
            return result

        try:
            return await loop.run_in_executor(None, _run)
        finally:
            logger.removeHandler(handler)
            await queue.put(None)

    task = asyncio.create_task(run_task())
    RUN_TASKS[run_id] = task

    async def event_generator():
        try:
            # First send the run_id so the frontend can cancel this run later
            yield f"event: run_id\ndata: {run_id}\n\n"
            while True:
                if await request.is_disconnected():
                    task.cancel()
                    break
                item = await queue.get()
                if item is None:
                    break
                yield f"event: log\ndata: {item}\n\n"

            result = await task
            payload = json.dumps(result)
            yield f"event: result\ndata: {payload}\n\n"
        except asyncio.CancelledError:
            # Task was cancelled (for example via the /scrape/linkedin/cancel endpoint).
            # Ensure the task is cancelled but stop the stream quietly without raising.
            task.cancel()
            return
        finally:
            RUN_TASKS.pop(run_id, None)

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@app.options("/scrape/competitors")
def options_competitors() -> Response:
    return Response(status_code=200)


@app.post("/scrape/competitors", response_model=ScrapeResponse)
def scrape_competitors(payload: CompetitorScrapeRequest):
    log_stream = StringIO()
    handler = logging.StreamHandler(log_stream)
    logger = logging.getLogger("finder")
    logger.addHandler(handler)
    try:
        result = discover_competitors(payload.brands)
        if not isinstance(result, dict):
            result = {"raw_result": result}
    finally:
        logger.removeHandler(handler)
    logs_value = log_stream.getvalue()
    return ScrapeResponse(status="SUCCESS", result=result, logs=logs_value or None)


@app.options("/scrape/csv")
def options_csv() -> Response:
    return Response(status_code=200)


@app.post("/scrape/csv", response_model=ScrapeResponse)
def scrape_csv(payload: CsvScrapeRequest):
    # Call the task implementation synchronously
    src = payload.source or "csv_upload"
    log_stream = StringIO()
    handler = logging.StreamHandler(log_stream)
    logger = logging.getLogger("finder")
    logger.addHandler(handler)
    try:
        result = process_shop_csv(payload.file_path, src)
        if not isinstance(result, dict):
            result = {"raw_result": result}
    finally:
        logger.removeHandler(handler)
    logs_value = log_stream.getvalue()
    return ScrapeResponse(status="SUCCESS", result=result, logs=logs_value or None)


@app.get("/scrape/csv/stream")
async def stream_csv(request: Request, file_path: str, source: str | None = None):
    """SSE stream for CSV/PDF processing using process_shop_csv.

    Streams all logs from the 'finder' logger as they are emitted, and finally
    sends a single `result` event with the JSON result of process_shop_csv.
    """

    src = source or "csv_upload"

    queue: asyncio.Queue[str | None] = asyncio.Queue()

    class QueueLogHandler(logging.Handler):  # type: ignore[misc]
        def emit(self, record: logging.LogRecord) -> None:
            try:
                msg = self.format(record)
                queue.put_nowait(msg)
            except Exception:
                # We never want logging failures to break the scrape
                pass

    handler = QueueLogHandler()
    handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
    logger = logging.getLogger("finder")
    logger.addHandler(handler)

    run_id = uuid.uuid4().hex

    async def run_task() -> dict:
        loop = asyncio.get_event_loop()

        def _run() -> dict:
            result = process_shop_csv(file_path, src, run_id=run_id)
            if not isinstance(result, dict):
                return {"raw_result": result}
            return result

        try:
            return await loop.run_in_executor(None, _run)
        finally:
            logger.removeHandler(handler)
            await queue.put(None)

    task = asyncio.create_task(run_task())
    RUN_TASKS[run_id] = task

    async def event_generator():
        try:
            # First send the run_id so the frontend can cancel this run later
            yield f"event: run_id\ndata: {run_id}\n\n"
            while True:
                if await request.is_disconnected():
                    task.cancel()
                    break
                item = await queue.get()
                if item is None:
                    break
                yield f"event: log\ndata: {item}\n\n"

            result = await task
            payload = json.dumps(result)
            yield f"event: result\ndata: {payload}\n\n"
        except asyncio.CancelledError:
            # Task was cancelled (for example via the /scrape/csv/cancel endpoint).
            # Ensure the task is cancelled but stop the stream quietly without raising.
            task.cancel()
            return
        finally:
            RUN_TASKS.pop(run_id, None)

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@app.post("/scrape/linkedin/cancel")
async def cancel_linkedin(payload: CancelRequest):
    request_cancel(payload.run_id)
    task = RUN_TASKS.pop(payload.run_id, None)
    if task is not None:
        task.cancel()
    return {"status": "CANCEL_REQUESTED"}


@app.post("/scrape/competitors/cancel")
async def cancel_competitors(payload: CancelRequest):
    request_cancel(payload.run_id)
    task = RUN_TASKS.pop(payload.run_id, None)
    if task is not None:
        task.cancel()
    return {"status": "CANCEL_REQUESTED"}


@app.post("/scrape/csv/cancel")
async def cancel_csv(payload: CancelRequest):
    # Log immediately so the user sees that a cancel was requested for this run
    logging.getLogger("finder").info(
        f"CSV/PDF cancel requested for run_id={payload.run_id}"
    )

    request_cancel(payload.run_id)
    task = RUN_TASKS.pop(payload.run_id, None)
    if task is not None:
        task.cancel()
    return {"status": "CANCEL_REQUESTED"}


@app.post("/scrape/linkedin/pause")
async def pause_linkedin(payload: CancelRequest):
    request_pause(payload.run_id)
    return {"status": "PAUSE_REQUESTED"}


@app.post("/scrape/linkedin/resume")
async def resume_linkedin(payload: CancelRequest):
    request_resume(payload.run_id)
    return {"status": "RESUME_REQUESTED"}


@app.post("/scrape/competitors/pause")
async def pause_competitors(payload: CancelRequest):
    request_pause(payload.run_id)
    return {"status": "PAUSE_REQUESTED"}


@app.post("/scrape/competitors/resume")
async def resume_competitors(payload: CancelRequest):
    request_resume(payload.run_id)
    return {"status": "RESUME_REQUESTED"}


@app.post("/scrape/csv/pause")
async def pause_csv(payload: CancelRequest):
    request_pause(payload.run_id)
    return {"status": "PAUSE_REQUESTED"}


@app.post("/scrape/csv/resume")
async def resume_csv(payload: CancelRequest):
    request_resume(payload.run_id)
    return {"status": "RESUME_REQUESTED"}
