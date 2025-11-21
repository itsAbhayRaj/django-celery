# Testing Quick Start Guide

This guide provides a quick reference for testing the Celery Email Project API.

## Quick Start

### 1. Prerequisites

Ensure all services are running:

```bash
# Terminal 1: Start Django server
python manage.py runserver

# Terminal 2: Start Redis
redis-server

# Terminal 3: Start Celery worker
celery -A celery_email_project worker --loglevel=info
```

### 2. Run Automated Tests

Run the automated test script:

```bash
python test_api.py
```

This will test all endpoints and provide a summary report.

### 3. Manual Testing

#### Using cURL

**Send Single Email:**
```bash
curl -X POST http://localhost:8000/email/send-email/ \
  -H "Content-Type: application/json" \
  -d '{"recipient":"test@example.com","subject":"Test","body":"Test body"}'
```

**Check Task Status:**
```bash
curl http://localhost:8000/email/email-status/<task_id>/
```

#### Using Python

```python
import requests

# Send email
response = requests.post(
    'http://localhost:8000/email/send-email/',
    json={
        'recipient': 'test@example.com',
        'subject': 'Test',
        'body': 'Test body'
    }
)
task_id = response.json()['task_id']

# Check status
status = requests.get(f'http://localhost:8000/email/email-status/{task_id}/')
print(status.json())
```

## Available Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/email/send-email/` | Send single email |
| POST | `/email/send-bulk-email/` | Send bulk email |
| GET | `/email/email-status/<task_id>/` | Check email task status |
| GET | `/start/?duration=N` | Start long-running task |
| GET | `/status/<task_id>/` | Check task status |

## Documentation

For detailed documentation with examples, see:
- **Full Documentation**: `API_TESTING_DOCUMENTATION.md`
- **Test Script**: `test_api.py`

## Common Test Scenarios

1. **Send Email** → Get `task_id` → Check status
2. **Send Bulk Email** → Get `task_id` → Monitor progress
3. **Start Long Task** → Get `task_id` → Monitor progress
4. **Test Validation** → Invalid email, missing fields

## Troubleshooting

- **Task stays PENDING**: Check Celery worker is running
- **Connection refused**: Check Django server is running
- **Email not sent**: Verify email settings in `settings.py`

For more details, see the full documentation in `API_TESTING_DOCUMENTATION.md`.

