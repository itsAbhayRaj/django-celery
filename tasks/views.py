from tasks.tasks import test_connection_task, long_running_task
from django.http import HttpResponse, JsonResponse
from celery.result import AsyncResult


# Create your views here.
def check_connection(request):
    result = test_connection_task.delay()
    return HttpResponse('Done')


def start_long_task(request):
    # Accept duration via query param, default to 5 seconds
    duration = request.GET.get('duration', '5')
    res = long_running_task.delay(duration)
    return JsonResponse({'task_id': res.id})


def task_status(request, task_id):
    res = AsyncResult(task_id)
    return JsonResponse({'state': res.state, 'meta': res.info})

# def start_long_task(request, duration):
#     result = long_running_task.delay(duration)
#     return HttpResponse('Long task started')