import os
from celery import Celery
from celery.schedules import crontab
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'celery_email_project.settings')

app = Celery('celery_email_project')

app.config_from_object('django.conf:settings', namespace='CELERY')

app.autodiscover_tasks()

# Periodic tasks configuration using crontab
app.conf.beat_schedule = {
    'daily-report-task': {
        'task': 'tasks.tasks.daily_report_task',
        'schedule': crontab(hour=9, minute=0), 
        'options': {'timezone': 'Asia/Kolkata'}
    },
    'weekly-cleanup-task': {
        'task': 'tasks.tasks.weekly_cleanup_task',
        'schedule': crontab(hour=2, minute=0, day_of_week=1),
        'options': {'timezone': 'Asia/Kolkata'}
    },
    'hourly-status-check-task': {
        'task': 'tasks.tasks.hourly_status_check_task',
        'schedule': crontab(minute=0),  
        'options': {'timezone': 'Asia/Kolkata'}
    },
}

@app.task(bind=True)
def debug_task(self):
    print(f'Request: {self.request!r}')