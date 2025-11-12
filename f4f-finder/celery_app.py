from celery import Celery
import os
from dotenv import load_dotenv

load_dotenv()

REDIS_URL = os.environ.get("REDIS_URL")

app = Celery("finder", broker=REDIS_URL, backend=REDIS_URL)

import tasks