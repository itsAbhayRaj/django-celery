from django.urls import path
from .views import (
    check_connection, start_long_task, task_status,
    ScheduleTaskView, ScheduleEmailView, ScheduledTasksListView,
    CancelTaskView, TaskHistoryView, UpdateTaskView, TaskDetailView,
    EmailPreferencesView, DashboardView, LoginView, LogoutView, UserProfileView,
    PeriodicTasksView, PeriodicTaskDetailView, TriggerPeriodicTaskView
)

urlpatterns = [
    path('', check_connection, name='check_connection'),
    path('start/', start_long_task, name='start_long_task'),
    path('status/<str:task_id>/', task_status, name='task_status'),
    
    path('api/login/', LoginView.as_view(), name='login'),
    path('api/logout/', LogoutView.as_view(), name='logout'),
    path('api/profile/', UserProfileView.as_view(), name='user_profile'),
    
    path('api/schedule-task/', ScheduleTaskView.as_view(), name='schedule_task'),
    path('api/cancel-task/<str:task_id>/', CancelTaskView.as_view(), name='cancel_task'),
    path('api/update-task/<str:task_id>/', UpdateTaskView.as_view(), name='update_task'),
    path('api/scheduled-tasks/', ScheduledTasksListView.as_view(), name='scheduled_tasks'),
    path('api/scheduled-tasks/<str:task_id>/', TaskDetailView.as_view(), name='task_detail'),
    
    path('api/schedule-email/', ScheduleEmailView.as_view(), name='schedule_email'),
    path('api/task-history/', TaskHistoryView.as_view(), name='task_history'),
    path('api/email-preferences/', EmailPreferencesView.as_view(), name='email_preferences'),
    path('api/dashboard/', DashboardView.as_view(), name='dashboard'),
]