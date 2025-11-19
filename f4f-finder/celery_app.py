from celery import Celery
import os
from dotenv import load_dotenv

load_dotenv()

REDIS_URL = os.environ.get("REDIS_URL")

# Create Celery app with tasks included
app = Celery(
    "finder",
    broker=REDIS_URL,
    backend=REDIS_URL,
    include=['tasks']
)

# Import tasks to register them (must be after app creation)
import tasks