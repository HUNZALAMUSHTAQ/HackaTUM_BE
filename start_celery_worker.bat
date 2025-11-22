@echo off
echo Starting Celery Worker for Windows...
echo.
echo Make sure Redis is running on localhost:6379
echo.
celery -A celery_app worker --loglevel=info --pool=solo
pause

