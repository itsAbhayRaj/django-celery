import os
from celery import Celery

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'celery_email_project.settings')

app = Celery('celery_email_project')

app.config_from_object('django.conf:settings', namespace='CELERY')

# CELERY Beat settings
app.conf.beat_schedule = {
    ''
}

app.autodiscover_tasks()

@app.task(bind=True)
def debug_task(self):
    print(f'Request: {self.request!r}')