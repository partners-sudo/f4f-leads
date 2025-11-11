import os
from celery import Celery

redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")

app = Celery("finder", broker=redis_url, backend=redis_url)
app.conf.update(task_serializer="json", result_serializer="json")

@app.task
def validate_domain(domain):
    try:
        r = requests.get(f"https://{domain}", timeout=5)
        return {"domain": domain, "status_code": r.status_code}
    except Exception as e:
        return {"domain": domain, "error": str(e)}