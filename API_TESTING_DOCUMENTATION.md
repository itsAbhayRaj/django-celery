# API Testing Documentation


---

## Prerequisites

Before testing, ensure:
- Django server is running: `python manage.py runserver`
- Redis is running: `redis-server`
- Celery worker is running: `celery -A celery_email_project worker --loglevel=info`
- Required dependencies are installed: `pip install -r requirements.txt`

---

## Base URL

```
http://localhost:8000
```

---

## Email API Endpoints

### 1. Send Single Email

**Endpoint:** `POST /email/send-email/`

**Description:** Sends an email to a single recipient asynchronously using Celery.

**Request Body:**
```json
{
    "recipient": "recipient@example.com",
    "subject": "Test Email Subject",
    "body": "This is the plain text body of the email",
    "html_message": "<h1>HTML Content</h1><p>This is HTML formatted email</p>"
}
```

**Response (202 Accepted):**
```json
{
    "task_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
}
```

**Error Response (400 Bad Request):**
```json
{
    "recipient": ["Enter a valid email address."],
    "subject": ["This field is required."]
}
```

---

### 2. Send Bulk Email

**Endpoint:** `POST /email/send-bulk-email/`

**Description:** Sends an email to multiple recipients asynchronously using Celery.

**Request Body:**
```json
{
    "recipients": [
        "recipient1@example.com",
        "recipient2@example.com",
        "recipient3@example.com"
    ],
    "subject": "Bulk Email Subject",
    "body": "This email is sent to multiple recipients",
    "html_message": "<h1>Bulk Email</h1><p>Sent to multiple recipients</p>"
}
```

**Response (202 Accepted):**
```json
{
    "task_id": "b2c3d4e5-f6g7-8901-bcde-f12345678901"
}
```

**Error Response (400 Bad Request):**
```json
{
    "recipients": ["This field is required."],
    "subject": ["This field is required."]
}
```

---

### 3. Check Email Task Status

**Endpoint:** `GET /email/email-status/<task_id>/`

**Description:** Retrieves the status of an email sending task.

**URL Parameters:**
- `task_id` (string): The task ID returned from send-email or send-bulk-email endpoints

**Response (200 OK):**
```json
{
    "state": "SUCCESS",
    "info": {
        "status": "sent",
        "recipient": "recipient@example.com"
    }
}
```

**Possible States:**
- `PENDING`: Task is waiting to be processed
- `PROGRESS`: Task is currently being processed
- `SUCCESS`: Task completed successfully
- `FAILURE`: Task failed
- `REVOKED`: Task was cancelled

**Example Response (Pending):**
```json
{
    "state": "PENDING",
    "info": null
}
```

**Example Response (Failure):**
```json
{
    "state": "FAILURE",
    "info": {
        "status": "failed",
        "reason": "Invalid email address"
    }
}
```

---

## Testing Examples

### Using cURL

#### 1. Send Single Email
```bash
curl -X POST http://localhost:8000/email/send-email/ \
  -H "Content-Type: application/json" \
  -d '{
    "recipient": "test@example.com",
    "subject": "Test Email",
    "body": "This is a test email",
    "html_message": "<h1>Test</h1><p>HTML content</p>"
  }'
```

#### 2. Send Bulk Email
```bash
curl -X POST http://localhost:8000/email/send-bulk-email/ \
  -H "Content-Type: application/json" \
  -d '{
    "recipients": ["user1@example.com", "user2@example.com"],
    "subject": "Bulk Email Test",
    "body": "This is a bulk email test"
  }'
```

#### 3. Check Email Task Status
```bash
# Replace <task_id> with actual task ID from previous response
curl -X GET http://localhost:8000/email/email-status/<task_id>/
```
---

## Test Scenarios

### Scenario 1: Successful Single Email Send

**Steps:**
1. Send a POST request to `/email/send-email/` with valid data
2. Receive task_id in response
3. Poll `/email/email-status/<task_id>/` until state is SUCCESS
4. Verify email was sent

**Expected Result:**
- Status code: 202
- Task state eventually becomes SUCCESS
- Email is received by recipient

---

### Scenario 2: Invalid Email Address

**Steps:**
1. Send a POST request to `/email/send-email/` with invalid email
2. Check response

**Request:**
```json
{
    "recipient": "invalid-email",
    "subject": "Test",
    "body": "Test body"
}
```

**Expected Result:**
- Status code: 400
- Error message indicating invalid email format

---

### Scenario 3: Missing Required Fields

**Steps:**
1. Send a POST request to `/email/send-email/` without required fields
2. Check response

**Request:**
```json
{
    "recipient": "test@example.com"
}
```

**Expected Result:**
- Status code: 400
- Error messages for missing fields (subject, body)

---

### Scenario 4: Bulk Email with Multiple Recipients

**Steps:**
1. Send a POST request to `/email/send-bulk-email/` with multiple recipients
2. Receive task_id
3. Monitor task status
4. Verify all recipients receive email

**Expected Result:**
- Status code: 202
- Task completes successfully
- All recipients receive the email

---

### Scenario 5: Long-Running Task Progress Monitoring

**Steps:**
1. Send GET request to `/start/?duration=15`
2. Receive task_id
3. Poll `/status/<task_id>/` every second
4. Observe progress updates

**Expected Result:**
- Task state progresses: PENDING → PROGRESS → SUCCESS
- Progress meta shows current/total values
- Task completes after specified duration

---

### Scenario 6: Task Status Check for Non-existent Task

**Steps:**
1. Send GET request to `/email/email-status/invalid-task-id/`
2. Check response

**Expected Result:**
- Status code: 200
- State may be PENDING or error info returned

---

### Scenario 7: Email with HTML Content

**Steps:**
1. Send email with html_message field
2. Verify HTML is rendered correctly in email client

**Request:**
```json
{
    "recipient": "test@example.com",
    "subject": "HTML Email Test",
    "body": "Plain text fallback",
    "html_message": "<html><body><h1>Hello</h1><p>This is <b>bold</b> text</p></body></html>"
}
```

**Expected Result:**
- Email sent successfully
- HTML content is rendered in email client
- Plain text body is used as fallback

---

### Scenario 8: Concurrent Email Requests

**Steps:**
1. Send multiple email requests simultaneously
2. Verify all tasks are queued and processed
3. Check each task status independently

**Expected Result:**
- All requests return 202 with unique task_ids
- Tasks are processed asynchronously
- All emails are eventually sent

## Notes

1. **Task IDs**: Task IDs are UUIDs returned immediately when a task is queued. Use these to check task status.

2. **Asynchronous Processing**: All email sending and long-running tasks are processed asynchronously. The API returns immediately with a task_id.

3. **Status Polling**: For long-running tasks, poll the status endpoint periodically to check progress.

4. **Error Handling**: Always check the response status codes and handle errors appropriately.

5. **Email Configuration**: Ensure email settings in `settings.py` are configured correctly for email sending to work.

6. **Redis and Celery**: Both Redis (broker) and Celery worker must be running for tasks to be processed.

---