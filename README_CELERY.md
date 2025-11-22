# Celery Background Worker Setup

This project uses Celery for asynchronous background task processing, specifically for generating preference questions using AI.

## Prerequisites

1. **Redis** - Message broker for Celery
   - Download Redis for Windows: https://github.com/microsoftarchive/redis/releases
   - Or use Docker: `docker run -d -p 6379:6379 redis:latest`
   - Or use WSL2 with Redis

2. **Python Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

## Running the Application

### 1. Start Redis

**Option A: Using Docker (Recommended)**
```bash
docker run -d -p 6379:6379 --name redis redis:latest
```

**Option B: Using Windows Redis**
- Download and install Redis for Windows
- Start Redis server

**Option C: Using WSL2**
```bash
wsl
sudo apt-get install redis-server
sudo service redis-server start
```

### 2. Start Celery Worker

**Windows (using batch file):**
```bash
start_celery_worker.bat
```

**Or manually:**
```bash
celery -A celery_app worker --loglevel=info --pool=solo
```

**Note:** On Windows, you must use `--pool=solo` instead of the default prefork pool.

### 3. Start FastAPI Server

In a separate terminal:
```bash
uvicorn main:app --reload
```

## Configuration

### Environment Variables

You can configure Celery using environment variables:

- `CELERY_BROKER_URL`: Redis broker URL (default: `redis://localhost:6379/0`)
- `CELERY_RESULT_BACKEND`: Result backend URL (default: `redis://localhost:6379/0`)

Example:
```bash
set CELERY_BROKER_URL=redis://localhost:6379/0
set CELERY_RESULT_BACKEND=redis://localhost:6379/0
```

## Monitoring Tasks

### Check Task Status

You can check the status of a task using the task_id returned from the API:

```python
from celery_tasks import generate_questions_task

# Get task result
task = generate_questions_task.AsyncResult(task_id)
print(task.state)  # PENDING, STARTED, SUCCESS, FAILURE, RETRY
print(task.result)  # Task result when completed
```

### Flower (Optional - Task Monitoring UI)

Install Flower:
```bash
pip install flower
```

Run Flower:
```bash
celery -A celery_app flower
```

Access at: http://localhost:5555

## Task Details

### Task: `generate_preference_questions`

- **Purpose**: Generate AI-powered questions for a preference
- **Parameters**:
  - `preference_id` (int): ID of the preference
  - `user_context` (str): Optional user context for personalization
- **Retry**: Automatically retries up to 3 times on failure
- **Timeout**: 5 minutes maximum execution time

## Troubleshooting

### Worker not starting on Windows

Make sure you're using `--pool=solo`:
```bash
celery -A celery_app worker --loglevel=info --pool=solo
```

### Redis connection error

1. Check if Redis is running:
   ```bash
   redis-cli ping
   ```
   Should return: `PONG`

2. Check Redis port (default: 6379)

3. Verify connection string in `celery_app.py`

### Tasks not executing

1. Check Celery worker logs for errors
2. Verify Redis is accessible
3. Check task is properly registered: `celery -A celery_app inspect registered`

## Production Deployment

For production, consider:

1. **Use a proper message broker**: RabbitMQ or Redis cluster
2. **Multiple workers**: Run multiple worker processes
3. **Monitoring**: Use Flower or Celery monitoring tools
4. **Error handling**: Set up proper logging and alerting
5. **Task priorities**: Configure task priorities if needed

Example production worker command:
```bash
celery -A celery_app worker --loglevel=info --concurrency=4 --max-tasks-per-child=1000
```

