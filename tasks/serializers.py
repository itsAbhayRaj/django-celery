from rest_framework import serializers
from tasks.models import ScheduledTask, TaskHistory, EmailPreferences
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import datetime


class EmailPreferencesSerializer(serializers.ModelSerializer):
    timezone = serializers.SerializerMethodField()
    
    class Meta:
        model = EmailPreferences
        fields = [
            'id', 'user', 'timezone', 'email', 'birthday', 'anniversary',
            'birthday_reminder_enabled', 'anniversary_reminder_enabled',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def get_timezone(self, obj):
        """Convert timezone object to string for JSON serialization"""
        if obj.timezone:
            return str(obj.timezone)
        return None


class ScheduledTaskSerializer(serializers.ModelSerializer):
    user_username = serializers.CharField(source='user.username', read_only=True)
    timezone = serializers.SerializerMethodField()
    
    class Meta:
        model = ScheduledTask
        fields = [
            'id', 'task_id', 'task_name', 'task_type', 'status',
            'schedule_time', 'crontab_expression', 'task_args', 'task_kwargs',
            'user', 'user_username', 'timezone', 'description',
            'created_at', 'updated_at', 'executed_at',
            'retry_count', 'max_retries'
        ]
        read_only_fields = [
            'id', 'task_id', 'status', 'created_at', 'updated_at',
            'executed_at', 'retry_count'
        ]
    
    def get_timezone(self, obj):
        if obj.timezone:
            return str(obj.timezone)
        return None


class TaskHistorySerializer(serializers.ModelSerializer):
    scheduled_task_name = serializers.CharField(source='scheduled_task.task_name', read_only=True)
    
    class Meta:
        model = TaskHistory
        fields = [
            'id', 'scheduled_task', 'scheduled_task_name', 'task_id',
            'task_name', 'status', 'result', 'error_message', 'traceback',
            'execution_time', 'executed_at'
        ]
        read_only_fields = ['id', 'executed_at']


class ScheduleTaskSerializer(serializers.Serializer):
    task_name = serializers.CharField(help_text="Celery task name (e.g., 'tasks.tasks.email_scheduler_task')")
    schedule_time = serializers.DateTimeField(required=False, allow_null=True)
    crontab_expression = serializers.CharField(
        required=False,
        allow_null=True,
        help_text="Crontab expression (e.g., '0 9 * * *' for daily at 9 AM)"
    )
    task_type = serializers.ChoiceField(
        choices=ScheduledTask.TASK_TYPES,
        default='one_time'
    )
    task_args = serializers.ListField(required=False, default=list)
    task_kwargs = serializers.DictField(required=False, default=dict)
    timezone = serializers.CharField(default='Asia/Kolkata')
    description = serializers.CharField(required=False, allow_blank=True, default='')
    max_retries = serializers.IntegerField(default=3, min_value=0, max_value=10)
    
    def validate(self, data):
        schedule_time = data.get('schedule_time')
        crontab_expression = data.get('crontab_expression')
        
        if not schedule_time and not crontab_expression:
            raise serializers.ValidationError(
                "Either 'schedule_time' or 'crontab_expression' must be provided"
            )
        
        if schedule_time and crontab_expression:
            raise serializers.ValidationError(
                "Cannot specify both 'schedule_time' and 'crontab_expression'"
            )
        
        return data


class ScheduleEmailSerializer(serializers.Serializer):
    recipient = serializers.EmailField()
    subject = serializers.CharField(max_length=255)
    body = serializers.CharField()
    html_message = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    schedule_time = serializers.DateTimeField(required=False, allow_null=True)
    timezone = serializers.CharField(default='Asia/Kolkata')
    from_email = serializers.EmailField(required=False, allow_null=True)
    
    def validate_schedule_time(self, value):
        if value and value < timezone.now():
            raise serializers.ValidationError("Schedule time cannot be in the past")
        return value


class UpdateTaskSerializer(serializers.Serializer):
    schedule_time = serializers.DateTimeField(required=False, allow_null=True)
    crontab_expression = serializers.CharField(required=False, allow_null=True)
    task_kwargs = serializers.DictField(required=False)
    enabled = serializers.BooleanField(required=False)


class BirthdayAnniversaryReminderSerializer(serializers.Serializer):
    user_id = serializers.IntegerField()
    email = serializers.EmailField()
    timezone = serializers.CharField(default='Asia/Kolkata')
    birthday = serializers.DateField(required=False, allow_null=True)
    anniversary = serializers.DateField(required=False, allow_null=True)
    birthday_reminder_enabled = serializers.BooleanField(default=True)
    anniversary_reminder_enabled = serializers.BooleanField(default=True)


class LoginSerializer(serializers.Serializer):
    username = serializers.CharField(required=True)
    password = serializers.CharField(required=True, write_only=True)


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name', 'date_joined']
        read_only_fields = ['id', 'date_joined']
