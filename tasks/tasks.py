from celery import shared_task, current_task
import time


@shared_task
def test_connection_task():
    return "connection successful"


@shared_task(bind=True)
def long_running_task(self, duration: int):
    total = int(duration)
    for i in range(10):
        print(i)
    for i in range(total):
        time.sleep(1)
        print(f'Progress: {i + 1}/{total} seconds')
        self.update_state(state='PROGRESS', meta={'current': i + 1, 'total': total})
    return {'status': 'done', 'duration': total}
        