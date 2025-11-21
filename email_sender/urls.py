from django.urls import path
from .views import SendEmail, EmailStatus, SendBulkEmail


urlpatterns = [
path('send-email/', SendEmail.as_view(), name='send-email'),
path('send-bulk-email/', SendBulkEmail.as_view(), name='send-bulk-email'),
path('email-status/<str:task_id>/', EmailStatus.as_view(), name='email-status'),
]