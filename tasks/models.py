from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from timezone_field import TimeZoneField
import json
import uuid


class EmailPreferences(models.Model):
    """Model to store user email preferences and schedules"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='email_preferences')
    timezone = TimeZoneField(default='Asia/Kolkata')
    email = models.EmailField()
    birthday = models.DateField(null=True, blank=True)
    anniversary = models.DateField(null=True, blank=True)
    birthday_reminder_enabled = models.BooleanField(default=True)
    anniversary_reminder_enabled = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = "Email Preferences"
        unique_together = ['user', 'email']

    def __str__(self):
        return f"{self.user.username} - {self.email}"


class ScheduledTask(models.Model):
    """Model to track dynamically created scheduled tasks"""
    TASK_TYPES = [
        ('one_time', 'One Time'),
        ('recurring', 'Recurring'),
        ('email', 'Email'),
        ('birthday', 'Birthday Reminder'),
        ('anniversary', 'Anniversary Reminder'),
        ('campaign', 'Email Campaign'),
    ]

    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('scheduled', 'Scheduled'),
        ('cancelled', 'Cancelled'),
    ]

    task_id = models.CharField(max_length=255, unique=True, db_index=True)
    task_name = models.CharField(max_length=255)
    task_type = models.CharField(max_length=20, choices=TASK_TYPES)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    
    # Schedule information
    schedule_time = models.DateTimeField(null=True, blank=True)
    crontab_expression = models.CharField(max_length=255, null=True, blank=True)
    periodic_task = models.ForeignKey(
        'django_celery_beat.PeriodicTask',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='scheduled_tasks'
    )
    
    # Task arguments
    task_args = models.JSONField(default=dict, blank=True)
    task_kwargs = models.JSONField(default=dict, blank=True)
    
    # Metadata
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    timezone = TimeZoneField(default='Asia/Kolkata')
    description = models.TextField(blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    executed_at = models.DateTimeField(null=True, blank=True)
    
    # Retry information
    retry_count = models.IntegerField(default=0)
    max_retries = models.IntegerField(default=3)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['task_id']),
            models.Index(fields=['status']),
            models.Index(fields=['schedule_time']),
        ]

    def __str__(self):
        return f"{self.task_name} ({self.task_id})"


class TaskHistory(models.Model):
    """Model to track task execution history"""
    STATUS_CHOICES = [
        ('success', 'Success'),
        ('failure', 'Failure'),
        ('retry', 'Retry'),
    ]

    scheduled_task = models.ForeignKey(
        ScheduledTask,
        on_delete=models.CASCADE,
        related_name='history',
        null=True,
        blank=True
    )
    task_id = models.CharField(max_length=255, db_index=True)
    task_name = models.CharField(max_length=255)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES)
    result = models.JSONField(default=dict, blank=True)
    error_message = models.TextField(blank=True)
    traceback = models.TextField(blank=True)
    execution_time = models.FloatField(null=True, blank=True)  # in seconds
    executed_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-executed_at']
        verbose_name_plural = "Task Histories"
        indexes = [
            models.Index(fields=['task_id']),
            models.Index(fields=['executed_at']),
            models.Index(fields=['status']),
        ]

    def __str__(self):
        return f"{self.task_name} - {self.status} at {self.executed_at}"
