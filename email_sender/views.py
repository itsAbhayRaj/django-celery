from django.shortcuts import render
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .serializers import EmailSerializer, BulkEmailSerializer
from .tasks import send_email_task, send_bulk_email_task
from celery.result import AsyncResult
from django.conf import settings
# Create your views here.

class SendEmail(APIView):
    def post(self, request):
        serializer = EmailSerializer(data=request.data)
        if serializer.is_valid():
            data = serializer.validated_data
            task = send_email_task.delay(
                recipient_email=data['recipient'],
                subject=data['subject'],
                message=data['body'],
                html_message=data.get('html_message'),
            )
            return Response({'task_id': task.id}, status=status.HTTP_202_ACCEPTED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    

class SendBulkEmail(APIView):
    def post(self, request):
        serializer = BulkEmailSerializer(data=request.data)
        if serializer.is_valid():
            data = serializer.validated_data
            task = send_bulk_email_task.delay(
                recipient_list=data['recipients'],
                subject=data['subject'],
                message=data['body'],
                html_message=data.get('html_message'),
            )
            return Response({'task_id': task.id}, status=status.HTTP_202_ACCEPTED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    
class EmailStatus(APIView):
    def get(self, request, task_id):
        result = AsyncResult(task_id)
        response_data = {
            'state': result.state,
            'info': result.info
        }
        return Response(response_data, status=status.HTTP_200_OK)