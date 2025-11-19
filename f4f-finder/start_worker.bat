@echo off
echo Starting Celery worker...
celery -A celery_app worker --loglevel=info

