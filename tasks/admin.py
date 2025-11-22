from django.contrib import admin
from tasks.models import ScheduledTask, TaskHistory, EmailPreferences
from django.utils.html import format_html
from django.urls import reverse
from django.utils import timezone


@admin.register(EmailPreferences)
class EmailPreferencesAdmin(admin.ModelAdmin):
    list_display = ['user', 'email', 'timezone', 'birthday', 'anniversary',
                    'birthday_reminder_enabled', 'anniversary_reminder_enabled', 'created_at']
    list_filter = ['birthday_reminder_enabled', 'anniversary_reminder_enabled', 'timezone', 'created_at']
    search_fields = ['user__username', 'user__email', 'email']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('User Information', {
            'fields': ('user', 'email', 'timezone')
        }),
        ('Reminder Settings', {
            'fields': ('birthday', 'anniversary', 'birthday_reminder_enabled', 'anniversary_reminder_enabled')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(ScheduledTask)
class ScheduledTaskAdmin(admin.ModelAdmin):
    list_display = ['task_id_short', 'task_name', 'task_type', 'status_badge', 'schedule_time',
                    'user', 'created_at', 'actions_column']
    list_filter = ['task_type', 'status', 'created_at', 'timezone']
    search_fields = ['task_id', 'task_name', 'description', 'user__username']
    readonly_fields = ['task_id', 'created_at', 'updated_at', 'executed_at', 'retry_count']
    
    fieldsets = (
        ('Task Information', {
            'fields': ('task_id', 'task_name', 'task_type', 'status', 'description')
        }),
        ('Schedule', {
            'fields': ('schedule_time', 'crontab_expression', 'periodic_task', 'timezone')
        }),
        ('Task Arguments', {
            'fields': ('task_args', 'task_kwargs'),
            'classes': ('collapse',)
        }),
        ('User & Metadata', {
            'fields': ('user', 'max_retries', 'retry_count')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at', 'executed_at'),
            'classes': ('collapse',)
        }),
    )
    
    def task_id_short(self, obj):
        return obj.task_id[:20] + '...' if len(obj.task_id) > 20 else obj.task_id
    task_id_short.short_description = 'Task ID'
    
    def status_badge(self, obj):
        colors = {
            'pending': 'gray',
            'scheduled': 'blue',
            'cancelled': 'black',
        }
        color = colors.get(obj.status, 'gray')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 8px; border-radius: 3px;">{}</span>',
            color,
            obj.status.upper()
        )
    status_badge.short_description = 'Status'
    
    def actions_column(self, obj):
        if obj.status in ['pending', 'scheduled']:
            return format_html(
                '<a href="{}" class="button">Cancel</a>',
                reverse('admin:tasks_scheduledtask_change', args=[obj.pk])
            )
        return '-'
    actions_column.short_description = 'Actions'


@admin.register(TaskHistory)
class TaskHistoryAdmin(admin.ModelAdmin):
    list_display = ['task_name', 'status_badge', 'execution_time_display', 'executed_at', 'scheduled_task_link']
    list_filter = ['status', 'task_name', 'executed_at']
    search_fields = ['task_id', 'task_name', 'error_message']
    readonly_fields = ['executed_at']
    
    fieldsets = (
        ('Task Information', {
            'fields': ('scheduled_task', 'task_id', 'task_name', 'status')
        }),
        ('Execution Details', {
            'fields': ('execution_time', 'executed_at', 'result')
        }),
        ('Error Information', {
            'fields': ('error_message', 'traceback'),
            'classes': ('collapse',)
        }),
    )
    
    def status_badge(self, obj):
        colors = {
            'success': 'green',
            'failure': 'red',
            'retry': 'orange',
        }
        color = colors.get(obj.status, 'gray')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 8px; border-radius: 3px;">{}</span>',
            color,
            obj.status.upper()
        )
    status_badge.short_description = 'Status'
    
    def execution_time_display(self, obj):
        if obj.execution_time:
            return f"{obj.execution_time:.2f}s"
        return '-'
    execution_time_display.short_description = 'Execution Time'
    
    def scheduled_task_link(self, obj):
        if obj.scheduled_task:
            return format_html(
                '<a href="{}">{}</a>',
                reverse('admin:tasks_scheduledtask_change', args=[obj.scheduled_task.pk]),
                obj.scheduled_task.task_name
            )
        return '-'
    scheduled_task_link.short_description = 'Scheduled Task'
