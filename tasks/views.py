from tasks.tasks import (
    test_connection_task, long_running_task, email_scheduler_task,
    create_dynamic_task, cancel_scheduled_task, update_scheduled_task
)
from tasks.models import ScheduledTask, TaskHistory, EmailPreferences
from tasks.serializers import (
    ScheduledTaskSerializer, TaskHistorySerializer, ScheduleTaskSerializer,
    ScheduleEmailSerializer, UpdateTaskSerializer, EmailPreferencesSerializer,
    BirthdayAnniversaryReminderSerializer, LoginSerializer, UserSerializer
)
from django.http import HttpResponse, JsonResponse
from celery.result import AsyncResult
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.decorators import api_view
from django.utils import timezone
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login, logout
from django.db.models import Q
from datetime import datetime
import pytz
from rest_framework.authtoken.models import Token


def check_connection(request):
    result = test_connection_task.delay()
    return HttpResponse('Done')


def start_long_task(request):
    duration = request.GET.get('duration', '5')
    res = long_running_task.delay(duration)
    return JsonResponse({'task_id': res.id})


def task_status(request, task_id):
    res = AsyncResult(task_id)
    return JsonResponse({'state': res.state, 'meta': res.info})

class ScheduleTaskView(APIView):
    
    def post(self, request):
        serializer = ScheduleTaskSerializer(data=request.data)
        if serializer.is_valid():
            data = serializer.validated_data
            
            user = request.user if request.user.is_authenticated else None
            
            try:
                scheduled_task = create_dynamic_task(
                    task_name=data['task_name'],
                    schedule_time=data.get('schedule_time'),
                    crontab_expression=data.get('crontab_expression'),
                    task_type=data['task_type'],
                    task_args=data.get('task_args', []),
                    task_kwargs=data.get('task_kwargs', {}),
                    user=user,
                    timezone_str=data.get('timezone', 'Asia/Kolkata'),
                    description=data.get('description', ''),
                    max_retries=data.get('max_retries', 3)
                )
                
                response_serializer = ScheduledTaskSerializer(scheduled_task)
                return Response(response_serializer.data, status=status.HTTP_201_CREATED)
            except Exception as e:
                return Response(
                    {'error': f'Failed to create scheduled task: {str(e)}'},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class ScheduledTasksListView(APIView):
    
    def get(self, request):
        queryset = ScheduledTask.objects.all()
        
        task_type = request.query_params.get('task_type')
        status_filter = request.query_params.get('status')
        user_id = request.query_params.get('user_id')
        
        if task_type:
            queryset = queryset.filter(task_type=task_type)
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        if user_id:
            queryset = queryset.filter(user_id=user_id)
        
        
        serializer = ScheduledTaskSerializer(queryset, many=True)
        
        return Response({
            'count': queryset.count(),
            'results': serializer.data
        })


class CancelTaskView(APIView):
    
    def post(self, request, task_id):
        success = cancel_scheduled_task(task_id)
        
        if success:
            try:
                scheduled_task = ScheduledTask.objects.get(task_id=task_id)
                serializer = ScheduledTaskSerializer(scheduled_task)
                return Response(serializer.data, status=status.HTTP_200_OK)
            except ScheduledTask.DoesNotExist:
                return Response(
                    {'message': 'Task cancelled but not found in database'},
                    status=status.HTTP_200_OK
                )
        else:
            return Response(
                {'error': 'Failed to cancel task. Task may not exist or already completed.'},
                status=status.HTTP_404_NOT_FOUND
            )


class TaskHistoryView(APIView):
    
    def get(self, request):
        queryset = TaskHistory.objects.all()

        task_id = request.query_params.get('task_id')
        task_name = request.query_params.get('task_name')
        status_filter = request.query_params.get('status')
        scheduled_task_id = request.query_params.get('scheduled_task_id')
        
        if task_id:
            queryset = queryset.filter(task_id=task_id)
        if task_name:
            queryset = queryset.filter(task_name=task_name)
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        if scheduled_task_id:
            queryset = queryset.filter(scheduled_task_id=scheduled_task_id)
        
        serializer = TaskHistorySerializer(queryset, many=True)
        
        return Response({
            'count': queryset.count(),
            'results': serializer.data
        })


class UpdateTaskView(APIView):
    
    def put(self, request, task_id):
        serializer = UpdateTaskSerializer(data=request.data)
        if serializer.is_valid():
            data = serializer.validated_data
            
            scheduled_task = update_scheduled_task(
                task_id=task_id,
                schedule_time=data.get('schedule_time'),
                crontab_expression=data.get('crontab_expression'),
                task_kwargs=data.get('task_kwargs'),
                enabled=data.get('enabled')
            )
            
            if scheduled_task:
                response_serializer = ScheduledTaskSerializer(scheduled_task)
                return Response(response_serializer.data, status=status.HTTP_200_OK)
            else:
                return Response(
                    {'error': 'Task not found'},
                    status=status.HTTP_404_NOT_FOUND
                )
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class TaskDetailView(APIView):
    
    def get(self, request, task_id):
        try:
            scheduled_task = ScheduledTask.objects.get(task_id=task_id)
            serializer = ScheduledTaskSerializer(scheduled_task)
            
            history = TaskHistory.objects.filter(
                scheduled_task=scheduled_task
            ).order_by('-executed_at')[:10]
            history_serializer = TaskHistorySerializer(history, many=True)
            
            celery_status = None
            if scheduled_task.task_id:
                try:
                    result = AsyncResult(scheduled_task.task_id)
                    celery_status = {
                        'state': result.state,
                        'info': result.info
                    }
                except:
                    pass
            
            return Response({
                'task': serializer.data,
                'history': history_serializer.data,
                'celery_status': celery_status
            })
        except ScheduledTask.DoesNotExist:
            return Response(
                {'error': 'Task not found'},
                status=status.HTTP_404_NOT_FOUND
            )


class ScheduleEmailView(APIView):
    
    def post(self, request):
        serializer = ScheduleEmailSerializer(data=request.data)
        if serializer.is_valid():
            data = serializer.validated_data
            
            user = request.user if request.user.is_authenticated else None
            timezone_str = data.get('timezone', 'Asia/Kolkata')
            
            email_data = {
                'recipient': data['recipient'],
                'subject': data['subject'],
                'body': data['body'],
                'html_message': data.get('html_message'),
                'from_email': data.get('from_email'),
            }
            
            schedule_time = data.get('schedule_time')
            
            try:
                if schedule_time:
                    if timezone.is_naive(schedule_time):
                        user_tz = pytz.timezone(timezone_str)
                        schedule_time = user_tz.localize(schedule_time)
                    
                    scheduled_task = create_dynamic_task(
                        task_name='tasks.tasks.email_scheduler_task',
                        schedule_time=schedule_time,
                        task_type='email',
                        task_kwargs={
                            'email_data': email_data,
                            'schedule_time': schedule_time.isoformat() if schedule_time else None
                        },
                        user=user,
                        timezone_str=timezone_str,
                        description=f"Email to {data['recipient']}: {data['subject']}"
                    )
                    
                    response_serializer = ScheduledTaskSerializer(scheduled_task)
                    return Response(response_serializer.data, status=status.HTTP_201_CREATED)
                else:
                    result = email_scheduler_task.delay(
                        email_data=email_data,
                        schedule_time=None
                    )
                    return Response(
                        {'task_id': result.id, 'status': 'sent_immediately'},
                        status=status.HTTP_202_ACCEPTED
                    )
            except Exception as e:
                return Response(
                    {'error': f'Failed to schedule email: {str(e)}'},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)



class EmailPreferencesView(APIView):
    
    def get(self, request):
        user_id = request.query_params.get('user_id')
        if user_id:
            preferences = EmailPreferences.objects.filter(user_id=user_id)
        else:
            preferences = EmailPreferences.objects.all()
        
        serializer = EmailPreferencesSerializer(preferences, many=True)
        return Response(serializer.data)
    
    def post(self, request):
        serializer = BirthdayAnniversaryReminderSerializer(data=request.data)
        if serializer.is_valid():
            data = serializer.validated_data
            
            try:
                user = User.objects.get(id=data['user_id'])
                email_pref, created = EmailPreferences.objects.update_or_create(
                    user=user,
                    email=data['email'],
                    defaults={
                        'timezone': data.get('timezone', 'Asia/Kolkata'),
                        'birthday': data.get('birthday'),
                        'anniversary': data.get('anniversary'),
                        'birthday_reminder_enabled': data.get('birthday_reminder_enabled', True),
                        'anniversary_reminder_enabled': data.get('anniversary_reminder_enabled', True),
                    }
                )
                
                response_serializer = EmailPreferencesSerializer(email_pref)
                return Response(
                    response_serializer.data,
                    status=status.HTTP_201_CREATED if created else status.HTTP_200_OK
                )
            except User.DoesNotExist:
                return Response(
                    {'error': 'User not found'},
                    status=status.HTTP_404_NOT_FOUND
                )
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class DashboardView(APIView):
    
    def get(self, request):
        total_tasks = ScheduledTask.objects.count()
        pending_tasks = ScheduledTask.objects.filter(status='pending').count()
        scheduled_tasks = ScheduledTask.objects.filter(status='scheduled').count()
        cancelled_tasks = ScheduledTask.objects.filter(status='cancelled').count()
        
        recent_tasks = ScheduledTask.objects.order_by('-created_at')[:10]
        recent_history = TaskHistory.objects.order_by('-executed_at')[:10]
        
        task_stats_by_type = {}
        for task_type, _ in ScheduledTask.TASK_TYPES:
            task_stats_by_type[task_type] = ScheduledTask.objects.filter(task_type=task_type).count()
        
        return Response({
            'statistics': {
                'total_tasks': total_tasks,
                'pending': pending_tasks,
                'scheduled': scheduled_tasks,
                'cancelled': cancelled_tasks,
                'by_type': task_stats_by_type
            },
            'recent_tasks': ScheduledTaskSerializer(recent_tasks, many=True).data,
            'recent_history': TaskHistorySerializer(recent_history, many=True).data
        })


class LoginView(APIView):
    
    permission_classes = []  
    
    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        if serializer.is_valid():
            username = serializer.validated_data['username']
            password = serializer.validated_data['password']
            
            user = authenticate(request, username=username, password=password)
            
            if user is not None:
                login(request, user)
                
                token, created = Token.objects.get_or_create(user=user)
                
                user_serializer = UserSerializer(user)
                
                return Response({
                    'message': 'Login successful',
                    'token': token.key,
                    'user': user_serializer.data
                }, status=status.HTTP_200_OK)
            else:
                return Response(
                    {'error': 'Invalid username or password'},
                    status=status.HTTP_401_UNAUTHORIZED
                )
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class LogoutView(APIView):
    
    def post(self, request):
        try:
            token = Token.objects.get(user=request.user)
            token.delete()
        except Token.DoesNotExist:
            pass
        
        logout(request)
        
        return Response(
            {'message': 'Logout successful'},
            status=status.HTTP_200_OK
        )


class UserProfileView(APIView):
    
    def get(self, request):
        serializer = UserSerializer(request.user)
        return Response(serializer.data, status=status.HTTP_200_OK)


class PeriodicTasksView(APIView):
    
    def get(self, request):
        from celery_email_project.celery import app as celery_app
        
        beat_schedule = celery_app.conf.beat_schedule or {}
        
        periodic_tasks = []
        for task_name, task_config in beat_schedule.items():
            schedule = task_config.get('schedule', {})
            schedule_info = {}
            
            if hasattr(schedule, 'minute'):
                schedule_info['minute'] = str(schedule.minute)
            if hasattr(schedule, 'hour'):
                schedule_info['hour'] = str(schedule.hour)
            if hasattr(schedule, 'day_of_week'):
                schedule_info['day_of_week'] = str(schedule.day_of_week)
            if hasattr(schedule, 'day_of_month'):
                schedule_info['day_of_month'] = str(schedule.day_of_month)
            if hasattr(schedule, 'month_of_year'):
                schedule_info['month_of_year'] = str(schedule.month_of_year)
            
            schedule_description = self._get_schedule_description(schedule)
            
            periodic_tasks.append({
                'name': task_name,
                'task': task_config.get('task', ''),
                'schedule': schedule_info,
                'schedule_description': schedule_description,
                'options': task_config.get('options', {}),
                'args': task_config.get('args', []),
                'kwargs': task_config.get('kwargs', {})
            })
        
        return Response({
            'count': len(periodic_tasks),
            'tasks': periodic_tasks
        })
    
    def _get_schedule_description(self, schedule):
        """Generate human-readable description of the schedule"""
        if hasattr(schedule, 'minute') and hasattr(schedule, 'hour'):
            minute = str(schedule.minute)
            hour = str(schedule.hour)
            day_of_week = str(schedule.day_of_week) if hasattr(schedule, 'day_of_week') else '*'
            
            if minute == '0' and hour == '*' and day_of_week == '*':
                return "Every hour"
            elif minute == '0' and hour != '*' and day_of_week == '*':
                return f"Daily at {hour}:00"
            elif minute == '0' and hour != '*' and day_of_week != '*':
                days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
                if day_of_week.isdigit():
                    day_name = days[int(day_of_week) - 1] if 1 <= int(day_of_week) <= 7 else day_of_week
                    return f"Every {day_name} at {hour}:00"
                return f"Every {day_of_week} at {hour}:00"
        
        return "Custom schedule"


class PeriodicTaskDetailView(APIView):
    
    def get(self, request, task_name):
        from celery_email_project.celery import app as celery_app
        
        beat_schedule = celery_app.conf.beat_schedule or {}
        
        if task_name not in beat_schedule:
            return Response(
                {'error': f'Periodic task "{task_name}" not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        task_config = beat_schedule[task_name]
        schedule = task_config.get('schedule', {})
        
        schedule_info = {}
        if hasattr(schedule, 'minute'):
            schedule_info['minute'] = str(schedule.minute)
        if hasattr(schedule, 'hour'):
            schedule_info['hour'] = str(schedule.hour)
        if hasattr(schedule, 'day_of_week'):
            schedule_info['day_of_week'] = str(schedule.day_of_week)
        if hasattr(schedule, 'day_of_month'):
            schedule_info['day_of_month'] = str(schedule.day_of_month)
        if hasattr(schedule, 'month_of_year'):
            schedule_info['month_of_year'] = str(schedule.month_of_year)
        
        schedule_description = self._get_schedule_description(schedule)
        
        recent_history = TaskHistory.objects.filter(
            task_name=task_config.get('task', '')
        ).order_by('-executed_at')[:10]
        history_serializer = TaskHistorySerializer(recent_history, many=True)
        
        return Response({
            'name': task_name,
            'task': task_config.get('task', ''),
            'schedule': schedule_info,
            'schedule_description': schedule_description,
            'options': task_config.get('options', {}),
            'args': task_config.get('args', []),
            'kwargs': task_config.get('kwargs', {}),
            'recent_executions': history_serializer.data
        })
    
    def _get_schedule_description(self, schedule):
        """Generate human-readable description of the schedule"""
        if hasattr(schedule, 'minute') and hasattr(schedule, 'hour'):
            minute = str(schedule.minute)
            hour = str(schedule.hour)
            day_of_week = str(schedule.day_of_week) if hasattr(schedule, 'day_of_week') else '*'
            
            if minute == '0' and hour == '*' and day_of_week == '*':
                return "Every hour"
            elif minute == '0' and hour != '*' and day_of_week == '*':
                return f"Daily at {hour}:00"
            elif minute == '0' and hour != '*' and day_of_week != '*':
                days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
                if day_of_week.isdigit():
                    day_name = days[int(day_of_week) - 1] if 1 <= int(day_of_week) <= 7 else day_of_week
                    return f"Every {day_name} at {hour}:00"
                return f"Every {day_of_week} at {hour}:00"
        
        return "Custom schedule"


class TriggerPeriodicTaskView(APIView):
    
    def post(self, request, task_name):
        from celery_email_project.celery import app as celery_app
        
        beat_schedule = celery_app.conf.beat_schedule or {}
        
        if task_name not in beat_schedule:
            return Response(
                {'error': f'Periodic task "{task_name}" not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        task_config = beat_schedule[task_name]
        task_path = task_config.get('task', '')
        
        if not task_path:
            return Response(
                {'error': 'Task path not found in configuration'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            module_path, task_func_name = task_path.rsplit('.', 1)
            module = __import__(module_path, fromlist=[task_func_name])
            task_func = getattr(module, task_func_name)
            
            result = task_func.delay()
            
            return Response({
                'message': f'Task "{task_name}" triggered successfully',
                'task_id': result.id,
                'status': 'triggered'
            }, status=status.HTTP_202_ACCEPTED)
            
        except Exception as e:
            return Response(
                {'error': f'Failed to trigger task: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )