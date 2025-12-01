from fastapi import FastAPI, Response
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
