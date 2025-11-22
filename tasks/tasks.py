from celery import shared_task, current_task, current_app
from celery.exceptions import Retry
import time
from django.utils import timezone
from django.core.mail import send_mail
from django.conf import settings
import logging
from datetime import datetime, timedelta
from django_celery_beat.models import PeriodicTask, CrontabSchedule, IntervalSchedule, ClockedSchedule
from tasks.models import ScheduledTask, TaskHistory, EmailPreferences
from django.contrib.auth.models import User
import json
import uuid
from typing import Dict, Any, Optional
from django.utils.timezone import make_aware, localtime
import pytz

logger = logging.getLogger('email_tasks')


def send_failure_notification(task_name: str, task_id: str, error_message: str):
    try:
        from django.contrib.auth.models import User
        admin_users = User.objects.filter(is_superuser=True)
        
        if admin_users.exists():
            admin_emails = [user.email for user in admin_users if user.email]
            
            if admin_emails:
                subject = f"Task Failure Alert: {task_name}"
                body = f"""
Task Name: {task_name}
Task ID: {task_id}
Error: {error_message}
Time: {timezone.now()}

This task has failed after all retry attempts.
Please check the task history for more details.
                """
                
                send_mail(
                    subject=subject,
                    message=body,
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=admin_emails,
                    fail_silently=True,
                )
    except Exception:
        pass

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

@shared_task
def daily_report_task():
    logger.info("Daily report task started")
    
    try:
        report_data = {
            'date': timezone.now().date().isoformat(),
            'timestamp': timezone.now().isoformat(),
            'message': 'Daily report generated successfully',
        }
        logger.info(f"Daily report data: {report_data}")
        print(f"[Daily Report] {report_data}")
        return report_data
    except Exception as e:
        logger.exception(f"Daily report task failed: {e}")
        raise

@shared_task
def weekly_cleanup_task():
    logger.info("Weekly cleanup task started")
    
    try:
        cleanup_data = {
            'date': timezone.now().date().isoformat(),
            'timestamp': timezone.now().isoformat(),
            'message': 'Weekly cleanup completed successfully',
        }
        logger.info(f"Weekly cleanup completed: {cleanup_data}")
        print(f"[WEEKLY CLEANUP] {cleanup_data}")
        return cleanup_data
    except Exception as e:
        logger.exception(f"Weekly cleanup task failed: {e}")
        raise

@shared_task
def hourly_status_check_task():
    logger.info("Hourly status check task started")
    
    try:
        status_data = {
            'timestamp': timezone.now().isoformat(),
            'message': 'Hourly status check completed successfully!',
        }
        logger.info(f"Hourly status check completed: {status_data}")
        print(f"[HOURLY STATUS CHECK] {status_data}")
        return status_data
    except Exception as e:
        logger.exception(f"Hourly status check task failed: {e}")
        raise


@shared_task(bind=True, max_retries=3)
def email_scheduler_task(self, email_data: Dict[str, Any], schedule_time: Optional[str] = None):
    task_id = self.request.id
    
    try:
        if schedule_time:
            schedule_dt = datetime.fromisoformat(schedule_time.replace('Z', '+00:00'))
            if timezone.is_naive(schedule_dt):
                schedule_dt = make_aware(schedule_dt)
            
            now = timezone.now()
            if schedule_dt > now:
                delay = (schedule_dt - now).total_seconds()
                return self.retry(countdown=delay, exc=None)
        
        recipient = email_data.get('recipient')
        subject = email_data.get('subject', 'No Subject')
        body = email_data.get('body', '')
        html_message = email_data.get('html_message')
        from_email = email_data.get('from_email', settings.DEFAULT_FROM_EMAIL)
        
        send_mail(
            subject=subject,
            message=body,
            from_email=from_email,
            recipient_list=[recipient],
            html_message=html_message,
            fail_silently=False,
        )
        
        TaskHistory.objects.create(
            task_id=task_id,
            task_name='email_scheduler_task',
            status='success',
            result={'status': 'sent', 'recipient': recipient}
        )
        
        return {'status': 'sent', 'recipient': recipient}
        
    except Exception as e:
        TaskHistory.objects.create(
            task_id=task_id,
            task_name='email_scheduler_task',
            status='failure',
            error_message=str(e)
        )
        
        if self.request.retries < self.max_retries:
            retry_delay = 60 * (2 ** self.request.retries)
            raise self.retry(exc=e, countdown=retry_delay)
        
        send_failure_notification('email_scheduler_task', task_id, str(e))
        raise


@shared_task(bind=True, max_retries=3)
def birthday_reminder_task(self, user_id: int, email_preference_id: int):
    task_id = self.request.id
    
    try:
        email_pref = EmailPreferences.objects.get(id=email_preference_id, user_id=user_id)
        
        if not email_pref.birthday_reminder_enabled or not email_pref.birthday:
            return {'status': 'skipped'}
        
        user_tz = pytz.timezone(str(email_pref.timezone))
        today_local = timezone.now().astimezone(user_tz).date()
        birthday_this_year = email_pref.birthday.replace(year=today_local.year)
        
        if birthday_this_year == today_local:
            user_name = email_pref.user.get_full_name() or email_pref.user.username
            subject = f"Happy Birthday {user_name}!"
            body = f"Dear {user_name},\n\nWishing you a wonderful birthday!\n\nBest regards,\nYour Email System"
            
            send_mail(
                subject=subject,
                message=body,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[email_pref.email],
                fail_silently=False,
            )
            
            TaskHistory.objects.create(
                task_id=task_id,
                task_name='birthday_reminder_task',
                status='success',
                result={'status': 'sent', 'recipient': email_pref.email}
            )
            
            return {'status': 'sent', 'recipient': email_pref.email}
        
        return {'status': 'skipped'}
            
    except Exception as e:
        TaskHistory.objects.create(
            task_id=task_id,
            task_name='birthday_reminder_task',
            status='failure',
            error_message=str(e)
        )
        
        if self.request.retries < self.max_retries:
            retry_delay = 60 * (2 ** self.request.retries)
            raise self.retry(exc=e, countdown=retry_delay)
        
        send_failure_notification('birthday_reminder_task', task_id, str(e))
        raise


@shared_task(bind=True, max_retries=3)
def anniversary_reminder_task(self, user_id: int, email_preference_id: int):
    task_id = self.request.id
    
    try:
        email_pref = EmailPreferences.objects.get(id=email_preference_id, user_id=user_id)
        
        if not email_pref.anniversary_reminder_enabled or not email_pref.anniversary:
            return {'status': 'skipped'}
        
        user_tz = pytz.timezone(str(email_pref.timezone))
        today_local = timezone.now().astimezone(user_tz).date()
        anniversary_this_year = email_pref.anniversary.replace(year=today_local.year)
        
        if anniversary_this_year == today_local:
            user_name = email_pref.user.get_full_name() or email_pref.user.username
            subject = f"Happy Anniversary {user_name}!"
            body = f"Dear {user_name},\n\nCongratulations on your anniversary!\n\nBest regards,\nYour Email System"
            
            send_mail(
                subject=subject,
                message=body,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[email_pref.email],
                fail_silently=False,
            )
            
            TaskHistory.objects.create(
                task_id=task_id,
                task_name='anniversary_reminder_task',
                status='success',
                result={'status': 'sent', 'recipient': email_pref.email}
            )
            
            return {'status': 'sent', 'recipient': email_pref.email}
        
        return {'status': 'skipped'}
            
    except Exception as e:
        TaskHistory.objects.create(
            task_id=task_id,
            task_name='anniversary_reminder_task',
            status='failure',
            error_message=str(e)
        )
        
        if self.request.retries < self.max_retries:
            retry_delay = 60 * (2 ** self.request.retries)
            raise self.retry(exc=e, countdown=retry_delay)
        
        send_failure_notification('anniversary_reminder_task', task_id, str(e))
        raise


@shared_task
def check_birthdays_and_anniversaries():
    email_prefs = EmailPreferences.objects.filter(
        birthday_reminder_enabled=True
    ).exclude(birthday__isnull=True)
    
    for pref in email_prefs:
        try:
            user_tz = pytz.timezone(str(pref.timezone))
            today_local = timezone.now().astimezone(user_tz).date()
            birthday_this_year = pref.birthday.replace(year=today_local.year)
            
            if birthday_this_year == today_local:
                birthday_reminder_task.delay(pref.user.id, pref.id)
        except Exception:
            pass
    
    anniversary_prefs = EmailPreferences.objects.filter(
        anniversary_reminder_enabled=True
    ).exclude(anniversary__isnull=True)
    
    for pref in anniversary_prefs:
        try:
            user_tz = pytz.timezone(str(pref.timezone))
            today_local = timezone.now().astimezone(user_tz).date()
            anniversary_this_year = pref.anniversary.replace(year=today_local.year)
            
            if anniversary_this_year == today_local:
                anniversary_reminder_task.delay(pref.user.id, pref.id)
        except Exception:
            pass
    
    return {'status': 'checked'}


@shared_task(bind=True, max_retries=3)
def email_campaign_task(self, recipients: list, subject: str, body: str, html_message: Optional[str] = None):
    task_id = self.request.id
    
    try:
        from_email = settings.DEFAULT_FROM_EMAIL
        sent_count = 0
        
        for recipient in recipients:
            try:
                send_mail(
                    subject=subject,
                    message=body,
                    from_email=from_email,
                    recipient_list=[recipient],
                    html_message=html_message,
                    fail_silently=False,
                )
                sent_count += 1
            except Exception:
                pass
        
        TaskHistory.objects.create(
            task_id=task_id,
            task_name='email_campaign_task',
            status='success',
            result={'status': 'sent', 'count': sent_count}
        )
        
        return {'status': 'sent', 'count': sent_count}
        
    except Exception as e:
        TaskHistory.objects.create(
            task_id=task_id,
            task_name='email_campaign_task',
            status='failure',
            error_message=str(e)
        )
        
        if self.request.retries < self.max_retries:
            retry_delay = 60 * (2 ** self.request.retries)
            raise self.retry(exc=e, countdown=retry_delay)
        
        send_failure_notification('email_campaign_task', task_id, str(e))
        raise


def create_dynamic_task(
    task_name: str,
    schedule_time: Optional[datetime] = None,
    crontab_expression: Optional[str] = None,
    task_type: str = 'one_time',
    task_args: Optional[list] = None,
    task_kwargs: Optional[dict] = None,
    user: Optional[User] = None,
    timezone_str: str = 'Asia/Kolkata',
    description: str = '',
    max_retries: int = 3
) -> ScheduledTask:
    unique_task_id = f"{task_name}_{uuid.uuid4().hex[:8]}"
    
    task_args = task_args or []
    task_kwargs = task_kwargs or {}
    
    scheduled_task = ScheduledTask.objects.create(
        task_id=unique_task_id,
        task_name=task_name,
        task_type=task_type,
        status='pending',
        schedule_time=schedule_time,
        crontab_expression=crontab_expression,
        task_args=task_args,
        task_kwargs=task_kwargs,
        user=user,
        timezone=timezone_str,
        description=description,
        max_retries=max_retries
    )
    
    if crontab_expression:
        parts = crontab_expression.split()
        if len(parts) == 5:
            minute, hour, day_of_month, month, day_of_week = parts
            
            crontab_schedule, _ = CrontabSchedule.objects.get_or_create(
                minute=minute,
                hour=hour,
                day_of_month=day_of_month,
                month_of_year=month,
                day_of_week=day_of_week,
                timezone=pytz.timezone(timezone_str)
            )
            
            periodic_task = PeriodicTask.objects.create(
                name=unique_task_id,
                task=task_name,
                crontab=crontab_schedule,
                enabled=True,
                args=json.dumps(task_args),
                kwargs=json.dumps(task_kwargs),
            )
            
            scheduled_task.periodic_task = periodic_task
            scheduled_task.status = 'scheduled'
            scheduled_task.save()
    
    elif schedule_time:
        if timezone.is_naive(schedule_time):
            user_tz = pytz.timezone(timezone_str)
            schedule_time = user_tz.localize(schedule_time)
        
        schedule_time_utc = schedule_time.astimezone(pytz.UTC)
        
        clocked_schedule = ClockedSchedule.objects.create(
            clocked_time=schedule_time_utc
        )
        
        periodic_task = PeriodicTask.objects.create(
            name=unique_task_id,
            task=task_name,
            clocked=clocked_schedule,
            one_off=True,
            enabled=True,
            args=json.dumps(task_args),
            kwargs=json.dumps(task_kwargs),
        )
        
        scheduled_task.periodic_task = periodic_task
        scheduled_task.status = 'scheduled'
        scheduled_task.save()
    
    return scheduled_task


def cancel_scheduled_task(task_id: str) -> bool:
    
    try:
        scheduled_task = ScheduledTask.objects.get(task_id=task_id)
        
        if scheduled_task.periodic_task:
            scheduled_task.periodic_task.enabled = False
            scheduled_task.periodic_task.save()
        
        from celery_email_project.celery import app as celery_app
        celery_app.control.revoke(task_id, terminate=True)
        
        scheduled_task.status = 'cancelled'
        scheduled_task.save()
        
        return True
    except ScheduledTask.DoesNotExist:
        logger.error(f"ScheduledTask not found: {task_id}")
        return False
    except Exception as e:
        logger.exception(f"Error cancelling task {task_id}: {e}")
        return False


def update_scheduled_task(
    task_id: str,
    schedule_time: Optional[datetime] = None,
    crontab_expression: Optional[str] = None,
    task_kwargs: Optional[dict] = None,
    enabled: Optional[bool] = None
) -> Optional[ScheduledTask]:
   
    try:
        scheduled_task = ScheduledTask.objects.get(task_id=task_id)
        
        if task_kwargs:
            scheduled_task.task_kwargs.update(task_kwargs)
            scheduled_task.save()
        
        if scheduled_task.periodic_task:
            if enabled is not None:
                scheduled_task.periodic_task.enabled = enabled
            if task_kwargs:
                scheduled_task.periodic_task.kwargs = json.dumps(scheduled_task.task_kwargs)
            scheduled_task.periodic_task.save()
        
        if schedule_time:
            scheduled_task.schedule_time = schedule_time
            scheduled_task.save()
        
        if crontab_expression:
            scheduled_task.crontab_expression = crontab_expression
            scheduled_task.save()
        
        return scheduled_task
    except ScheduledTask.DoesNotExist:
        logger.error(f"ScheduledTask not found: {task_id}")
        return None
    except Exception as e:
        logger.exception(f"Error updating task {task_id}: {e}")
        return None