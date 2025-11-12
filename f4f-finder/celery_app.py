from celery import Celery

import os

REDIS_URL = os.environ.get("REDIS_URL")

app = Celery("finder", broker=REDIS_URL, backend=REDIS_URL)

