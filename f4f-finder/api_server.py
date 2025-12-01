from fastapi import FastAPI, Response, Request
from starlette.responses import StreamingResponse
import asyncio
import json
import logging
from io import StringIO
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from tasks import (
    scrape_linkedin_companies,
    discover_competitors,
    process_shop_csv,
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


app = FastAPI()

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

    async def run_task() -> dict:
        loop = asyncio.get_event_loop()

        def _run() -> dict:
            result = discover_competitors(brand_list)
            if not isinstance(result, dict):
                return {"raw_result": result}
            return result

        try:
            return await loop.run_in_executor(None, _run)
        finally:
            logger.removeHandler(handler)
            await queue.put(None)

    task = asyncio.create_task(run_task())

    async def event_generator():
        try:
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
            task.cancel()
            raise

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

    async def run_task() -> dict:
        loop = asyncio.get_event_loop()

        def _run() -> dict:
            result = scrape_linkedin_companies(keyword)
            if not isinstance(result, dict):
                return {"raw_result": result}
            return result

        try:
            return await loop.run_in_executor(None, _run)
        finally:
            logger.removeHandler(handler)
            await queue.put(None)

    task = asyncio.create_task(run_task())

    async def event_generator():
        try:
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
            task.cancel()
            raise

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

    async def run_task() -> dict:
        loop = asyncio.get_event_loop()

        def _run() -> dict:
            result = process_shop_csv(file_path, src)
            if not isinstance(result, dict):
                return {"raw_result": result}
            return result

        try:
            return await loop.run_in_executor(None, _run)
        finally:
            logger.removeHandler(handler)
            await queue.put(None)

    task = asyncio.create_task(run_task())

    async def event_generator():
        try:
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
            task.cancel()
            raise

    return StreamingResponse(event_generator(), media_type="text/event-stream")
