from django.urls import path
from .views import check_connection, start_long_task, task_status

urlpatterns = [
    path('', check_connection, name='check_connection'),
    path('start/', start_long_task, name='start_long_task'),
    path('status/<str:task_id>/', task_status, name='task_status'),
]
