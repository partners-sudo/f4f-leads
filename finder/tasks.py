from celery import Celery
from dotenv import load_dotenv
import os, requests, json

load_dotenv()
REDIS_URL = os.getenv("REDIS_URL")

celery_app = Celery("finder", broker=REDIS_URL, backend=REDIS_URL)
celery_app.conf.update(task_serializer="json", result_serializer="json")

@celery_app.task
def validate_domain(domain):
    try:
        r = requests.get(f"https://{domain}", timeout=5)
        return {"domain": domain, "status_code": r.status_code}
    except Exception as e:
        return {"domain": domain, "error": str(e)}
