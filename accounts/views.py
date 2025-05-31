from django.shortcuts import render, redirect
from .models import CustomUser, UserTypes, PerformanceReview, Goal, ReviewScheduling, Review, ChatMessage, ActivityLog, Workspace
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from django.shortcuts import get_object_or_404
from datetime import datetime, timezone
from .models import CustomUser
from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from .models import Attend
from django.utils import timezone
from django.core.mail import send_mail
from django.conf import settings
from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import json
from .forms import TaskForm, TaskCommentForm
from django.db import models
from django.db.models import Count
from django.utils.timezone import now, timedelta
from django.contrib.auth.forms import PasswordChangeForm
from django import forms

class UserProfileForm(forms.ModelForm):
    class Meta:
        model = CustomUser
        fields = ['username', 'email', 'first_name', 'last_name']
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
        }

def user_login(request):
    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")
        
        user = authenticate(request, username=username, password=password)

        if user is not None:
            login(request, user)
            # Redirect based on user type
            if user.user_type == UserTypes.SUPERADMIN:
                return redirect('superadmin_dashboard')
            elif user.user_type == UserTypes.EMPLOYER:
                return redirect('employer_dashboard')  
            elif user.user_type == UserTypes.INTERN:
                return redirect('intern_dashboard', user_id=user.id)    
            else:
                return redirect('/')
        else: 
            if CustomUser.objects.filter(username=username).exists():
                messages.error(request, "Please enter correct password")
            else:
                messages.error(request, "Invalid login credentials")
            return redirect('user_login')

    return render(request, "registration/login.html")

@login_required
def chat_view(request, user_id):
    other_user = get_object_or_404(CustomUser, id=user_id)
    if request.user == other_user:
        messages.error(request, "Cannot chat with yourself.")
        return redirect('user_login')

    # Fetch chat messages between the two users
    messages_qs = ChatMessage.objects.filter(
        (models.Q(sender=request.user) & models.Q(receiver=other_user)) |
        (models.Q(sender=other_user) & models.Q(receiver=request.user))
    ).order_by('timestamp')

    context = {
        'other_user': other_user,
        'messages': messages_qs,
    }
    return render(request, 'chat/chat.html', context)

@login_required
@csrf_exempt
def send_message(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        receiver_id = data.get('receiver_id')
        message_text = data.get('message')

        receiver = get_object_or_404(CustomUser, id=receiver_id)
        chat_message = ChatMessage.objects.create(
            sender=request.user,
            receiver=receiver,
            message=message_text
        )
        chat_message.save()

        # Create notification for receiver
        from .models import Notification
        notification_message = f"New message from {request.user.username}"
        Notification.objects.create(
            user=receiver,
            notification_type='new_message',
            message=notification_message
        )

        return JsonResponse({'status': 'success', 'message': 'Message sent.'})
    return JsonResponse({'status': 'fail', 'message': 'Invalid request.'})

@login_required
def task_create(request):
    if request.method == 'POST':
        form = TaskForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            messages.success(request, 'Task created successfully.')
            return redirect('tasks_list')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = TaskForm()
    return render(request, 'admin/task_create.html', {'form': form})

@login_required
def task_detail(request, task_id):
    task = get_object_or_404(Goal, id=task_id)
    
    # Check if user has permission to view this task
    if request.user.user_type == UserTypes.SUPERADMIN:
        # Superadmin can view any task
        pass
    elif task.assigned_to != request.user:
        messages.error(request, "You don't have permission to view this task.")
        return redirect('user_login')
    
    comments = task.comments.all().order_by('-created_at')
    checkpoints = task.checkpoints.all().order_by('created_at')
    
    if request.method == 'POST':
        action = request.POST.get('action')
            
            # Handle document upload
        if 'document' in request.FILES:
                checkpoint.document = request.FILES['document']
                messages.success(request, 'Document uploaded successfully!')
            
            # Update progress status
                progress_status = request.POST.get('progress_status')
        if progress_status == 'completed':
                checkpoint.is_completed = True
                checkpoint.completed_at = timezone.now()
                checkpoint.completion_comment = request.POST.get('completion_notes', '')
        elif progress_status == 'in_progress':
                checkpoint.is_completed = False
                checkpoint.completed_at = None
                checkpoint.completion_comment = ''
        else:  # not_started
                checkpoint.is_completed = False
                checkpoint.completed_at = None
                checkpoint.completion_comment = ''
            
                checkpoint.save()
            
            # Update task progress
        completed_checkpoints = task.checkpoints.filter(is_completed=True)
        total_progress = sum(cp.progress_value for cp in completed_checkpoints)
        
        task.progress = total_progress
            
            # Update task status
        if total_progress == 100:
                task.status = 'completed'
                task.completed = True
        elif total_progress > 0:
                task.status = 'in_progress'
        else:
                task.status = 'pending'
            
        task.save()
            
            # Log the activity
        ActivityLog.objects.create(
                user=request.user,
                action=f'Updated checkpoint: {checkpoint.title} - {progress_status}'
            )
            
        messages.success(request, 'Progress updated successfully!')
            
        
            
        return redirect('task_detail', task_id=task.id)
    
    # Determine which template to use based on user type
    template = 'workspace/user_task_detail.html' if request.user.user_type != UserTypes.SUPERADMIN else 'workspace/task_detail.html'
    
    context = {
        'task': task,
        'comments': comments,
        'checkpoints': checkpoints,
    }
    return render(request, template, context)

@login_required
def user_list_by_role(request, role):
    # Validate role
    valid_roles = [choice[0] for choice in UserTypes.choices]
    if role not in valid_roles:
        messages.error(request, "Invalid user role specified.")
        return redirect('user_login')

    users = CustomUser.objects.filter(user_type=role)
    context = {
        'users': users,
        'role': role,
    }
    return render(request, 'chat/user_list.html', context)


# Create your views here.
def user_register(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        email = request.POST.get('email')
        password = request.POST.get('password')
        password2 = request.POST.get('password2')
        role = request.POST.get('role')

        # Validate passwords match
        if password != password2:
            messages.error(request, 'Passwords do not match')
            return redirect('user_register')

        # Validate role selection
        valid_roles = ['superadmin', 'employer', 'intern']
        if role not in valid_roles:
            messages.error(request, 'Invalid role selected')
            return redirect('user_register')

        try:
            # Create user
            user = CustomUser.objects.create_user(username=username, email=email, password=password)
            user.user_type = role
            
            # Assign role
            if role == 'superadmin':
                
                user.is_superuser = True
            elif role == 'employer':
                user.is_staff = True
            
            user.save()
            messages.success(request, 'Registration successful! Please login.')
            return redirect('user_login')

        except Exception as e:
            messages.error(request, f'Registration failed: {str(e)}')
            return redirect('user_register')

    return render(request, 'registration/register.html', {'roles': ['superadmin', 'employer', 'intern']})

@login_required
def superadmin_dashboard(request):
    if request.user.user_type != UserTypes.SUPERADMIN:
        return redirect('user_login')

    # Get all users except superadmin
    users = CustomUser.objects.exclude(user_type=UserTypes.SUPERADMIN)
    goals = Goal.objects.all()
    attendance_records = Attend.objects.filter(datetime__gte=now()-timedelta(days=30))
    performance_reviews = PerformanceReview.objects.all().order_by('-date')[:10]
    notifications = Goal.objects.filter(models.Q(deadline__lte=now() + timedelta(days=3)) | models.Q(status='missed'))

    # Get recent activity logs
    recent_activities = ActivityLog.objects.all().order_by('-timestamp')[:10]

    # Prepare data for charts
    user_type_counts = users.values('user_type').annotate(count=Count('id'))
    user_type_data = {ut['user_type']: ut['count'] for ut in user_type_counts}

    task_status_counts = goals.values('status').annotate(count=Count('id'))
    task_status_data = {ts['status']: ts['count'] for ts in task_status_counts}

    attendance_by_date_qs = attendance_records.extra({'date': "date(datetime)"}).values('date').annotate(count=Count('id')).order_by('date')
    attendance_by_date = {str(record['date']): record['count'] for record in attendance_by_date_qs}

    context = {
        'user_type_data': json.dumps(user_type_data),
        'task_status_data': json.dumps(task_status_data),
        'attendance_by_date': json.dumps(attendance_by_date),
        'performance_reviews': performance_reviews,
        'notifications': notifications,
        'users': users,
        'goals': goals,
        'attendance_records': attendance_records,
        'recent_activities': recent_activities,
        'user': request.user
    }
    return render(request, "admin/admin_dashboard.html", context)

@login_required
def superadmin_users_list(request):
    if request.user.user_type != UserTypes.SUPERADMIN:
        return redirect('user_login')

    users = CustomUser.objects.all()
    context = {
        'users': users,
    }
    return render(request, "superadmin/users_list.html", context)

@login_required
def superadmin_user_add(request):
    if request.user.user_type != UserTypes.SUPERADMIN:
        messages.error(request, 'You do not have permission to access this page.')
        return redirect('home')
    
    if request.method == 'POST':
        username = request.POST.get('username')
        email = request.POST.get('email')
        password = request.POST.get('password')
        password2 = request.POST.get('password2')
        user_type = request.POST.get('user_type')
        
        # Validate passwords match
        if password != password2:
            messages.error(request, 'Passwords do not match.')
            return redirect('superadmin_user_add')
        
        # Check if username or email already exists
        if CustomUser.objects.filter(username=username).exists():
            messages.error(request, 'Username already exists.')
            return redirect('superadmin_user_add')
        if CustomUser.objects.filter(email=email).exists():
            messages.error(request, 'Email already exists.')
            return redirect('superadmin_user_add')
        
        try:
            # Create user with proper role
            user = CustomUser.objects.create_user(
                username=username,
                email=email,
                password=password,
                user_type=user_type,
                is_active=True  # Ensure user is active
            )
            
            # Set additional permissions based on role
            if user_type == UserTypes.EMPLOYER:
                user.is_staff = True
                user.save()
            
            # Create workspace for the user
            workspace = Workspace.objects.create(
                name=f"{username}'s Workspace",
                owner=user
            )
            user.workspace = workspace
            user.save()
            
            # Log the activity
            ActivityLog.objects.create(
                user=request.user,
                action=f'Created new {user_type} user: {username}',
                details=f'Created user account for {username} with role {user_type}'
            )
            
            messages.success(request, f'User {username} created successfully.')
            return redirect('superadmin_users_list')
            
        except Exception as e:
            messages.error(request, f'Error creating user: {str(e)}')
            return redirect('superadmin_user_add')
    
    # Get user types for the form
    user_types = [(UserTypes.EMPLOYER, 'Employer'), (UserTypes.INTERN, 'Intern')]
    
    return render(request, 'superadmin/user_add.html', {
        'user_types': user_types
    })

@login_required
def users_list(request):
    if request.user.user_type != UserTypes.SUPERADMIN:
        return redirect('user_login')

    users = CustomUser.objects.exclude(user_type=UserTypes.ADMIN)
    context = {
        'users': users,
    }
    return render(request, "admin/users_list.html", context)

@login_required
def superadmin_user_delete(request, user_id):
    if request.user.user_type != UserTypes.SUPERADMIN:
        return redirect('user_login')

    try:
        user = get_object_or_404(CustomUser, id=user_id)
        
        # Prevent deleting the last superadmin
        if user.user_type == UserTypes.SUPERADMIN and CustomUser.objects.filter(user_type=UserTypes.SUPERADMIN).count() <= 1:
            messages.error(request, "Cannot delete the last superadmin user.")
            return redirect('superadmin_users_list')
        
        # Store username for the success message
        username = user.username
        
        # Delete related data
        # Delete user's tasks
        Goal.objects.filter(assigned_to=user).delete()
        
        # Delete user's performance reviews
        PerformanceReview.objects.filter(user=user).delete()
        
        # Delete user's attendance records
        Attend.objects.filter(attender=user).delete()
        
        # Delete user's chat messages
        ChatMessage.objects.filter(sender=user).delete()
        ChatMessage.objects.filter(receiver=user).delete()
        
        # Delete user's activity logs
        ActivityLog.objects.filter(user=user).delete()
        
        # Delete the user
        user.delete()
        
        messages.success(request, f"User '{username}' and all associated data have been deleted successfully.")
    except Exception as e:
        messages.error(request, f"Error deleting user: {str(e)}")
    
    return redirect('superadmin_users_list')

@login_required
def superadmin_user_edit(request, user_id):
    if request.user.user_type != UserTypes.SUPERADMIN:
        return redirect('user_login')

    user = get_object_or_404(CustomUser, id=user_id)

    if request.method == 'POST':
        user.email = request.POST.get('email')
        user.user_type = request.POST.get('user_type')
        user.save()
        messages.success(request, "User updated successfully.")
        return redirect('superadmin_users_list')

    context = {
        'user': user,
        'user_types': UserTypes.choices,
    }
    return render(request, "superadmin/user_edit.html", context)
        
@login_required
def tasks_list(request):
    if request.user.user_type != UserTypes.SUPERADMIN:
        return redirect('user_login')

    goals = Goal.objects.all().order_by('deadline')
    context = {
        'goals': goals,
    }
    return render(request, "admin/tasks_list.html", context)

@login_required
def attendance_list(request):
    if request.user.user_type != UserTypes.SUPERADMIN:
        return redirect('user_login')

    attendance_records = Attend.objects.all().order_by('-datetime')[:50]
    context = {
        'attendance_records': attendance_records,
    }
    return render(request, "admin/attendance_list.html", context)

@login_required
def notifications_list(request):
    if request.user.user_type != UserTypes.SUPERADMIN:
        return redirect('user_login')

    from django.utils.timezone import now, timedelta
    upcoming_deadline = now() + timedelta(days=3)
    goals = Goal.objects.all()
    notifications = goals.filter(models.Q(deadline__lte=upcoming_deadline) | models.Q(status='missed')).order_by('deadline')

    context = {
        'notifications': notifications,
    }
    return render(request, "admin/notifications_list.html", context)

@login_required
def user_profile(request):
    user = request.user
    if request.method == 'POST':
        profile_form = UserProfileForm(request.POST, instance=user)
        password_form = PasswordChangeForm(user, request.POST)
        if profile_form.is_valid() and password_form.is_valid():
            profile_form.save()
            password_form.save()
            update_session_auth_hash(request, password_form.user)  # Important to keep user logged in after password change
            messages.success(request, 'Your profile and password have been updated successfully.')
            return redirect('user_profile')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        profile_form = UserProfileForm(instance=user)
        password_form = PasswordChangeForm(user)

    context = {
        'profile_form': profile_form,
        'password_form': password_form,
    }
    return render(request, 'registration/profile.html', context)

def work_desc(request, user_id):
    user = get_object_or_404(CustomUser, id=user_id)
    # Fetching all performance reviews for the user
    performance_reviews = PerformanceReview.objects.filter(user=user).order_by("-id")[:3]
    upcoming_reviews = ReviewScheduling.objects.filter(user=user).order_by("-id")[:3]

    if "savePerformance" in request.POST:
        productivity_score = request.POST.get("productivity")
        punctuality_score = request.POST.get("punctuality")
        collaboration_score = request.POST.get("collaboration")
        goals = request.POST.get("goal")
        feedback = request.POST.get("feedbackText")


        try:
            performance_metrics = PerformanceReview.objects.create(
                user = user,
                productivity_score = productivity_score,
                punctuality_score = punctuality_score,
                collaboration_score = collaboration_score,
                goals = goals,
                feedback = feedback,
            )
            performance_metrics.save()
            messages.success(request, "Performance review saved successfully.")
        except ValueError as e:
            messages.error(request, f"Invalid input: {e}")
        except Exception as e:
            messages.error(request, f"An error occurred: {e}")
        return redirect("work_desc", user_id=user.id)
    # Handle Review Scheduling Form submission
    if "scheduleReview" in request.POST:  # Check if this is the review scheduling form
        review_title = request.POST.get("reviewTitle")
        review_date = request.POST.get("reviewDate")
        review_time = request.POST.get("reviewTime")

        try:
            upcoming_review = ReviewScheduling.objects.create(
                user=user,
                review_title=review_title,
                review_date=datetime.strptime(review_date, "%Y-%m-%d").date(),
                review_time=datetime.strptime(review_time, "%H:%M").time()
            )
            upcoming_review.save()
            messages.success(request, "Review scheduled successfully.")
        except Exception as e:
            messages.error(request, f"Error in scheduling review: {e}")

        return redirect("work_desc", user_id=user.id)


    context = {
        'user': user,
        'performance_reviews': performance_reviews,
        'upcoming_reviews': upcoming_reviews,

    }
    return render(request, "manager/work_desc.html", context)

# View performance details
def performance_details(request, review_id):
    review = get_object_or_404(PerformanceReview, id=review_id)
    user = review.user  # The user associated with the review



    data = {
        'review': review,
        'user': user,

    }

    return render(request, "manager/performance_details.html", data)

# for viewing all review
def allReview(request, user_id):
    allReviews = PerformanceReview.objects.filter(user_id=user_id).order_by("-id")

    data={
        'allReviews': allReviews,
    }
    return render(request, "manager/allReview.html", data)

# For Assing Goals


def assign_goal(request):
    if request.method == 'POST':
        description = request.POST.get('description')
        title = request.POST.get('title')  # Capture the title
        deadline = request.POST.get('deadline')
        if title.strip() and description.strip():  # Ensure title and description are not empty
            goal = Goal.objects.create(
                title=title,
                description=description,
                status='in_progress',
                progress=0,
                deadline=deadline if deadline else None  # Set deadline if provided
            )
            # Send email notification to assigned user if assigned_to is set
            if hasattr(goal, 'assigned_to') and goal.assigned_to and goal.assigned_to.email:
                subject = 'New Task Assigned'
                message = f'Hello {goal.assigned_to.username},\n\nYou have been assigned a new task: {goal.title}.\n\nDescription: {goal.description}\nDeadline: {goal.deadline}\n\nPlease check your dashboard for more details.'
                from_email = settings.DEFAULT_FROM_EMAIL if hasattr(settings, 'DEFAULT_FROM_EMAIL') else 'no-reply@example.com'
                recipient_list = [goal.assigned_to.email]
                send_mail(subject, message, from_email, recipient_list)
            messages.success(request, "Goal assigned successfully!")
        else:
            messages.error(request, "Goal title and description cannot be empty!")
        return redirect('assign_goal')  # Ensure this URL pattern is defined
    goals = Goal.objects.all()
    data={
        'goals': goals,
    }
    return render(request, 'manager/Work_desc.html', data)

def UpCommingReview(request):
    return render(request, "manager/UpCommingReview.html")


#Employer Dashboard
# For viewing all review
@login_required
def employer_dashboard(request):
    user = request.user
    if user.user_type != UserTypes.EMPLOYER:
        return redirect('user_login')  # Ensure only employers access this dashboard
    
    # Get all tasks assigned to the user
    tasks = Goal.objects.filter(assigned_to=user).order_by('-created_at')
    
    # Calculate task statistics
    total_tasks = tasks.count()
    completed_tasks = tasks.filter(status='completed')
    in_progress_tasks = tasks.filter(status='in_progress')
    missed_tasks = tasks.filter(status='missed')
    
    completed_count = completed_tasks.count()
    in_progress_count = in_progress_tasks.count()
    missed_count = missed_tasks.count()
    
    # Calculate completion rate
    completion_rate = 0
    if total_tasks > 0:
        completion_rate = int((completed_count / total_tasks) * 100)
    
    # Get recent in-progress tasks with their checkpoints, comments, and documents
    recent_tasks = in_progress_tasks.prefetch_related(
        'checkpoints',
        'checkpoints__comments',
        'checkpoints__document',
        'comments'
    ).order_by('-created_at')[:5]
    
    # For each task, calculate its progress based on completed checkpoints
    for task in recent_tasks:
        completed_checkpoints = task.checkpoints.filter(is_completed=True)
        total_progress = sum(cp.progress_value for cp in completed_checkpoints)
        task.progress = total_progress
        
        # Update task status if needed
        if total_progress == 100 and task.status != 'completed':
            task.status = 'completed'
            task.save()
        elif total_progress > 0 and task.status == 'pending':
            task.status = 'in_progress'
            task.save()
    
    # Get recent activity logs for the user
    recent_activities = ActivityLog.objects.filter(
        user=user
    ).order_by('-timestamp')[:10]
    
    # Create a dictionary to store activities for each task
    task_activities = {}
    for activity in recent_activities:
        # Extract task ID from activity action if it contains task information
        if 'task' in activity.action.lower():
            # Try to find task ID in the action string
            task_id = None
            if 'task id:' in activity.action.lower():
                try:
                    task_id = int(activity.action.split('task id:')[1].split()[0])
                except (IndexError, ValueError):
                    pass
            
            if task_id:
                if task_id not in task_activities:
                    task_activities[task_id] = []
                task_activities[task_id].append(activity)
    
    # Add activities to each task
    for task in recent_tasks:
        task.activities = task_activities.get(task.id, [])
    
    context = {
        'user': user,
        'total_tasks': total_tasks,
        'completed_count': completed_count,
        'in_progress_count': in_progress_count,
        'missed_count': missed_count,
        'completion_rate': completion_rate,
        'in_progress_tasks': recent_tasks,
    }
    
    return render(request, 'employer/employer_dashboard.html', context)


#intern
def intern_dashboard(request, user_id):
    user = get_object_or_404(CustomUser, id=user_id)
    if request.user != user and not request.user.is_superuser:
        return redirect('login')

    # Get all tasks assigned to the user
    tasks = Goal.objects.filter(assigned_to=user).order_by('-created_at')
    
    # Calculate task statistics
    total_tasks = tasks.count()
    completed_tasks = tasks.filter(status='completed')
    in_progress_tasks = tasks.filter(status='in_progress')
    missed_tasks = tasks.filter(status='missed')
    
    completed_count = completed_tasks.count()
    in_progress_count = in_progress_tasks.count()
    missed_count = missed_tasks.count()
    
    # Calculate completion rate
    completion_rate = 0
    if total_tasks > 0:
        completion_rate = int((completed_count / total_tasks) * 100)
    
    # Get recent in-progress tasks with their checkpoints
    recent_tasks = in_progress_tasks.prefetch_related('checkpoints')[:5]
    
    context = {
        'user': user,
        'total_tasks': total_tasks,
        'completed_count': completed_count,
        'in_progress_count': in_progress_count,
        'missed_count': missed_count,
        'completion_rate': completion_rate,
        'in_progress_tasks': recent_tasks,
    }
    
    return render(request, 'intern/intern_dashboard.html', context)

#View performance details for intern
def intern_performance_details(request, review_id):
    review = get_object_or_404(PerformanceReview, id=review_id)
    user = review.user  
    data = {
        'review': review,
        'user': user,
    }
    return render(request, "intern/intern_performance_detail.html", data)

#self-assessment
def Self_Assessment(request):
    if request.method == "POST":
        self_assessment_text = request.POST.get('selfAssessment')
        user = request.user
        if self_assessment_text:
            PerformanceReview.objects.create(
                user=user,
                productivity_score=0,  # Placeholder; adjust as needed
                punctuality_score=0,
                collaboration_score=0,
                goals="Self-Assessment",
                feedback=self_assessment_text,
            )
            messages.success(request, "Self-assessment submitted successfully!")
            return redirect('intern_dashboard', user_id=user.id)
        else:
            messages.error(request, "Self-assessment cannot be empty!")
    return render(request, "intern/Self_Assessment.html")

@login_required
def goals(request):
    user = request.user
    if user.user_type != UserTypes.INTERN:
        return redirect('user_login')  # Restrict to interns
    
    goals = Goal.objects.filter(assigned_to=user).order_by('-created_at')
    
    if request.method == "POST":
        goal_id = request.POST.get('goal_id')
        progress = request.POST.get('progress')
        comments = request.POST.get('comments')
        
        try:
            goal = Goal.objects.get(id=goal_id, assigned_to=user)
            progress = int(progress)
            if 0 <= progress <= 100:
                goal.progress = progress
                if progress == 100:
                    goal.completed = True
                    goal.status = 'completed'
                elif progress > 0:
                    goal.status = 'in_progress'
                if comments:
                    goal.description += f"\nUpdate: {comments}"
                goal.save()
                messages.success(request, "Goal progress updated successfully!")
            else:
                messages.error(request, "Progress must be between 0 and 100!")
        except Goal.DoesNotExist:
            messages.error(request, "Goal not found!")
        except ValueError:
            messages.error(request, "Invalid progress value!")
        return redirect('goals')
    
    context = {
        'user': user,
        'goals': goals,
    }
    return render(request, "intern/goals.html", context)

from django.core.mail import send_mail
from django.conf import settings

def assign_goals(request):
    users = CustomUser.objects.filter(user_type__in=[UserTypes.INTERN, UserTypes.EMPLOYER])
    if request.method == 'POST':
        title = request.POST.get('title')
        description = request.POST.get('description')
        deadline = request.POST.get('deadline')
        assigned_to_id = request.POST.get('assigned_to')
        
        try:
            # Check if a similar task already exists
            existing_task = Goal.objects.filter(
                title=title,
                assigned_to_id=assigned_to_id,
                created_at__gte=timezone.now() - timedelta(minutes=5)
            ).first()
            
            if existing_task:
                messages.error(request, 'A similar task was recently created for this user.')
                return redirect('assign_goals')
            
            assigned_to = CustomUser.objects.get(
                id=assigned_to_id,
                user_type__in=[UserTypes.INTERN, UserTypes.EMPLOYER],
                is_active=True
            )
            
            # Get or create workspace for the assigned user
            workspace, created = Workspace.objects.get_or_create(
                user=assigned_to,
                defaults={'name': f"{assigned_to.username}'s Workspace"}
            )
            
            # Create and save the goal
            goal = Goal.objects.create(
                title=title,
                description=description,
                deadline=deadline,
                assigned_to=assigned_to,
                workspace=workspace,
                status='in_progress',
                progress=0
            )
            
            # Send email notification to assigned user
            if assigned_to.email:
                subject = 'New Task Assigned'
                message = f'Hello {assigned_to.username},\n\nYou have been assigned a new task: {title}.\n\nDescription: {description}\nDeadline: {deadline}\n\nPlease check your dashboard for more details.'
                from_email = settings.DEFAULT_FROM_EMAIL if hasattr(settings, 'DEFAULT_FROM_EMAIL') else 'no-reply@example.com'
                recipient_list = [assigned_to.email]
                send_mail(subject, message, from_email, recipient_list)
            
            messages.success(request, 'Task assigned successfully!')
            return redirect('assign_goals')
            
        except CustomUser.DoesNotExist:
            messages.error(request, 'Selected user does not exist or is not active.')
        except Exception as e:
            messages.error(request, f'Error assigning task: {str(e)}')
    
    context = {
        'users': users
    }
    return render(request, 'manager/Work_desc.html', context)

@login_required
def goals_history(request):
    user = request.user
    if user.user_type != UserTypes.INTERN:
        return redirect('user_login')  # Restrict to interns
    
    # Fetch goals that are completed or past their deadline
    goals = Goal.objects.filter(
        assigned_to=user
    ).exclude(status='pending').order_by('-deadline')  # Exclude active pending goals
    
    context = {
        'user': user,
        'goals': goals,
    }
    return render(request, "intern/goals_history.html", context)

# For viewing all goals assigned to the user
@login_required
def employee_dashboard(request):
    user = request.user
    if user.user_type != UserTypes.EMPLOYER:
        return redirect('user_login')  # Ensure only employees access this dashboard
    
    performance_reviews = PerformanceReview.objects.filter(user=user).order_by('-date')[:3]
    goals = Goal.objects.filter(assigned_to=user).order_by('-created_at')
    goals_completed = goals.filter(completed=True).count()
    attendance_records = Attend.objects.filter(attender=user).order_by('-datetime')
    
    data = {
        'user': user,
        'performance_reviews': performance_reviews,
        'goals': goals,
        'goals_completed': goals_completed,
        'attendance_records': attendance_records,
    }
    return render(request, "employees/employee_dashboard.html", data)

def attendance_view(request):
    status = None
    if request.method == "POST":
        if request.user.is_authenticated:
            try:
                current_date = timezone.now().date()
                # Check if user has already marked attendance today
                existing_attendance = Attend.objects.filter(
                    attender=request.user,
                    datetime__date=current_date
                ).first()
                
                if existing_attendance:
                    status = 2  # Already marked attendance today
                else:
                    # Create new attendance record
                    attend_object = Attend(
                        attender=request.user,
                        datetime=timezone.now()
                    )
                    attend_object.save()
                    status = 1  # Successfully marked attendance
            except Exception as e:
                status = 0  # Error occurred
                messages.error(request, f"Error marking attendance: {str(e)}")
        else:
            status = 0  # User not authenticated
    
    # Get the attendance records for the logged-in user
    if request.user.is_authenticated:
        attendance_records = Attend.objects.filter(attender=request.user).order_by('-datetime')
    else:
        attendance_records = []

    context = {
        'status': status,
        'attendance_records': attendance_records,
        'today': timezone.now().date()
    }
    return render(request, "attendance/attendance.html", context)

@login_required
def admin_attendance_view(request):
    if request.user.user_type != UserTypes.SUPERADMIN:
        messages.error(request, "You don't have permission to view this page.")
        return redirect('user_login')
    
    # Get all attendance records
    attendance_records = Attend.objects.all().order_by('-datetime')
    
    # Get attendance statistics
    total_attendance = attendance_records.count()
    today_attendance = attendance_records.filter(datetime__date=timezone.now().date()).count()
    
    # Get attendance by user
    user_attendance = {}
    for record in attendance_records:
        user = record.attender
        if user not in user_attendance:
            user_attendance[user] = {
                'total': 0,
                'today': False
            }
        user_attendance[user]['total'] += 1
        if record.datetime.date() == timezone.now().date():
            user_attendance[user]['today'] = True
    
    context = {
        'attendance_records': attendance_records,
        'total_attendance': total_attendance,
        'today_attendance': today_attendance,
        'user_attendance': user_attendance,
        'today': timezone.now().date()
    }
    return render(request, "admin/attendance_list.html", context)

# For Logout
def logout_view(request):
    """
    Logs out the user and redirects to the homepage.
    """
    logout(request)
    return redirect('/')  # Redirect to the homepage or login page


def edit_review(request, review_id):
    review = get_object_or_404(Review, id=review_id)
    
    if request.method == "POST":
        # Get the data from the request
        productivity_score = request.POST.get("productivity_score")
        punctuality_score = request.POST.get("punctuality_score")
        collaboration_score = request.POST.get("collaboration_score")
        goals = request.POST.get("goals")
        feedback = request.POST.get("feedback")

        # Update the review instance
        review.productivity_score = productivity_score
        review.punctuality_score = punctuality_score
        review.collaboration_score = collaboration_score
        review.goals = goals
        review.feedback = feedback

        # Save the changes to the database
        review.save()

        # Redirect back to the details page or list
        return redirect('work_desc', review.user.id)

    # Render the same template with review details
    return render(request, "edit_review.html", {"review": review})

@login_required
def admin_dashboard(request):
    if request.user.user_type != UserTypes.ADMIN:
        return redirect('user_login')

    # Get all users except admin
    users = CustomUser.objects.exclude(user_type=UserTypes.ADMIN)
    goals = Goal.objects.all()
    attendance_records = Attend.objects.filter(datetime__gte=now()-timedelta(days=30))
    performance_reviews = PerformanceReview.objects.all().order_by('-date')[:10]
    notifications = Goal.objects.filter(models.Q(deadline__lte=now() + timedelta(days=3)) | models.Q(status='missed'))

    # Get recent activity logs
    recent_activities = ActivityLog.objects.all().order_by('-timestamp')[:10]

    # Prepare data for charts
    user_type_counts = users.values('user_type').annotate(count=Count('id'))
    user_type_data = {ut['user_type']: ut['count'] for ut in user_type_counts}

    task_status_counts = goals.values('status').annotate(count=Count('id'))
    task_status_data = {ts['status']: ts['count'] for ts in task_status_counts}

    # Get task statistics
    total_tasks = goals.count()
    completed_tasks = goals.filter(status='achieved').count()
    in_progress_tasks = goals.filter(status='in_progress').count()
    missed_tasks = goals.filter(status='missed').count()

    # Calculate completion rate
    completion_rate = (completed_tasks / total_tasks * 100) if total_tasks > 0 else 0

    # Get tasks by priority
    priority_counts = goals.values('priority').annotate(count=Count('id'))
    priority_data = {p['priority']: p['count'] for p in priority_counts}

    context = {
        'user_type_data': json.dumps(user_type_data),
        'task_status_data': json.dumps(task_status_data),
        'priority_data': json.dumps(priority_data),
        'performance_reviews': performance_reviews,
        'notifications': notifications,
        'users': users,
        'goals': goals,
        'attendance_records': attendance_records,
        'recent_activities': recent_activities,
        'total_tasks': total_tasks,
        'completed_tasks': completed_tasks,
        'in_progress_tasks': in_progress_tasks,
        'missed_tasks': missed_tasks,
        'completion_rate': round(completion_rate, 1),
        'user': request.user
    }
    return render(request, 'admin/admin_dashboard.html', context)

@login_required
def personal_workspace(request):
    """View for managing personal workspace and tasks."""
    # Get or create user's workspace
    workspace, created = Workspace.objects.get_or_create(user=request.user)
    
    # Get tasks for different statuses
    in_progress_tasks = workspace.get_in_progress_tasks()
    completed_tasks = workspace.get_completed_tasks()
    missed_tasks = workspace.get_missed_tasks()
    
    # Get task statistics
    total_tasks = workspace.get_tasks().count()
    completed_count = completed_tasks.count()
    in_progress_count = in_progress_tasks.count()
    missed_count = missed_tasks.count()
    
    # Calculate completion rate
    completion_rate = (completed_count / total_tasks * 100) if total_tasks > 0 else 0
    
    context = {
        'workspace': workspace,
        'in_progress_tasks': in_progress_tasks,
        'completed_tasks': completed_tasks,
        'missed_tasks': missed_tasks,
        'total_tasks': total_tasks,
        'completed_count': completed_count,
        'in_progress_count': in_progress_count,
        'missed_count': missed_count,
        'completion_rate': round(completion_rate, 1),
    }
    
    return render(request, 'workspace/personal_workspace.html', context)

@login_required
def update_workspace(request):
    """View for updating workspace settings."""
    if request.method == 'POST':
        workspace = request.user.workspace
        workspace.name = request.POST.get('name', workspace.name)
        workspace.description = request.POST.get('description', workspace.description)
        workspace.save()
        messages.success(request, 'Workspace updated successfully!')
        return redirect('personal_workspace')
    
    return render(request, 'workspace/update_workspace.html', {'workspace': request.user.workspace})

@login_required
def task_management(request):
    if request.user.user_type != UserTypes.SUPERADMIN:
        return redirect('user_login')

    # Get all tasks
    tasks = Goal.objects.all().order_by('deadline')
    
    # Get all registered users (EMPLOYER and INTERN) for task assignment
    users = CustomUser.objects.filter(
        user_type__in=[UserTypes.EMPLOYER, UserTypes.INTERN],
        is_active=True
    ).select_related('workspace').order_by('user_type', 'username')
    
    # Apply filters if any
    status = request.GET.get('status')
    priority = request.GET.get('priority')
    assigned_to = request.GET.get('assigned_to')
    
    if status:
        tasks = tasks.filter(status=status)
    if priority:
        tasks = tasks.filter(priority=priority)
    if assigned_to:
        tasks = tasks.filter(assigned_to_id=assigned_to)
    
    # Get task statistics
    total_tasks = tasks.count()
    completed_tasks = tasks.filter(status='achieved').count()
    in_progress_tasks = tasks.filter(status='in_progress').count()
    missed_tasks = tasks.filter(status='missed').count()
    
    context = {
        'tasks': tasks,
        'users': users,
        'total_tasks': total_tasks,
        'completed_tasks': completed_tasks,
        'in_progress_tasks': in_progress_tasks,
        'missed_tasks': missed_tasks,
    }
    return render(request, 'admin/task_management.html', context)

@login_required
def create_task(request):
    if request.user.user_type != UserTypes.SUPERADMIN:
        return redirect('user_login')
        
    if request.method == 'POST':
        title = request.POST.get('title')
        description = request.POST.get('description')
        priority = request.POST.get('priority')
        deadline = request.POST.get('deadline')
        tags = request.POST.get('tags')
        attachment = request.FILES.get('attachment')
        assigned_to_id = request.POST.get('assigned_to')
        user_role = request.POST.get('user_role')
        
        try:
            # Check if a similar task already exists
            existing_task = Goal.objects.filter(
                title=title,
                assigned_to_id=assigned_to_id,
                created_at__gte=timezone.now() - timedelta(minutes=5)
            ).first()
            
            if existing_task:
                messages.error(request, 'A similar task was recently created for this user.')
                return redirect('task_management')
            
            assigned_to = CustomUser.objects.get(
                id=assigned_to_id,
                user_type__in=[UserTypes.EMPLOYER, UserTypes.INTERN],
                is_active=True
            )
            
            # Verify that the assigned user matches the selected role
            if assigned_to.user_type != user_role:
                messages.error(request, 'Selected user does not match the chosen role.')
                return redirect('task_management')
            
            # Get or create workspace for the assigned user
            workspace, created = Workspace.objects.get_or_create(
                user=assigned_to,
                defaults={'name': f"{assigned_to.username}'s Workspace"}
            )
            
            # Create the task
            task = Goal.objects.create(
                title=title,
                description=description,
                priority=priority,
                deadline=deadline,
                tags=tags,
                attachment=attachment,
                status='in_progress',
                progress=0,
                assigned_to=assigned_to,
                workspace=workspace
            )
            
            # Send email notification
            if assigned_to.email:
                subject = 'New Task Assigned'
                message = f'Hello {assigned_to.username},\n\nYou have been assigned a new task: {title}.\n\nDescription: {description}\nDeadline: {deadline}\n\nPlease check your dashboard for more details.'
                from_email = settings.DEFAULT_FROM_EMAIL if hasattr(settings, 'DEFAULT_FROM_EMAIL') else 'no-reply@example.com'
                recipient_list = [assigned_to.email]
                send_mail(subject, message, from_email, recipient_list)

            # Create notification for assigned user
            from .models import Notification
            notification_message = f"You have been assigned a new task: {title}"
            Notification.objects.create(
                user=assigned_to,
                notification_type='new_task',
                message=notification_message
            )
            
            messages.success(request, 'Task created successfully!')
        except CustomUser.DoesNotExist:
            messages.error(request, 'Selected user does not exist or is not active.')
        except Exception as e:
            messages.error(request, f'Error creating task: {str(e)}')
            
    return redirect('task_management')

@login_required
def edit_task(request, task_id):
    task = get_object_or_404(Goal, id=task_id, workspace=request.user.workspace)
    
    if request.method == 'POST':
        task.title = request.POST.get('title')
        task.description = request.POST.get('description')
        task.priority = request.POST.get('priority')
        task.deadline = request.POST.get('deadline')
        task.tags = request.POST.get('tags')
        
        if 'attachment' in request.FILES:
            task.attachment = request.FILES['attachment']
        
        task.save()
        messages.success(request, 'Task updated successfully!')
        return redirect('task_management')
    
    return JsonResponse({
        'title': task.title,
        'description': task.description,
        'priority': task.priority,
        'deadline': task.deadline.strftime('%Y-%m-%dT%H:%M'),
        'tags': task.tags,
    })

@login_required
def delete_task(request, task_id):
    task = get_object_or_404(Goal, id=task_id, workspace=request.user.workspace)
    task.delete()
    messages.success(request, 'Task deleted successfully!')
    return redirect('task_management')

@login_required
def add_comment(request, task_id):
    task = get_object_or_404(Goal, id=task_id, workspace=request.user.workspace)
    
    if request.method == 'POST':
        data = json.loads(request.body)
        comment_text = data.get('comment')
        
        if comment_text:
            comment = TaskComment.objects.create(
                goal=task,
                user=request.user,
                comment=comment_text
            )
            return JsonResponse({
                'success': True,
                'comment': {
                    'comment': comment.comment,
                    'user': comment.user.username,
                    'created_at': comment.created_at.strftime('%Y-%m-%d %H:%M')
                }
            })
    
    return JsonResponse({'success': False})

@login_required
def task_analytics(request):
    if request.user.user_type != UserTypes.SUPERADMIN:
        messages.error(request, "You don't have permission to view this page.")
        return redirect('user_login')

    # Get all tasks
    all_tasks = Goal.objects.all()
    
    # Task status distribution
    status_counts = all_tasks.values('status').annotate(count=Count('id'))
    status_data = {
        'labels': [item['status'].title() for item in status_counts],
        'data': [item['count'] for item in status_counts]
    }
    
    # Task completion over time (last 30 days)
    thirty_days_ago = timezone.now() - timedelta(days=30)
    daily_completion = all_tasks.filter(
        status='completed',
        updated_at__gte=thirty_days_ago
    ).extra(
        select={'day': 'date(updated_at)'}
    ).values('day').annotate(count=Count('id')).order_by('day')
    
    completion_data = {
        'labels': [item['day'] for item in daily_completion],
        'data': [item['count'] for item in daily_completion]
    }
    
    # User-wise task distribution
    user_tasks = all_tasks.values('assigned_to__username').annotate(
        total=Count('id'),
        completed=Count('id', filter=models.Q(status='completed')),
        in_progress=Count('id', filter=models.Q(status='in_progress')),
        pending=Count('id', filter=models.Q(status='pending'))
    )
    
    user_data = {
        'labels': [item['assigned_to__username'] for item in user_tasks],
        'datasets': [
            {
                'label': 'Completed',
                'data': [item['completed'] for item in user_tasks]
            },
            {
                'label': 'In Progress',
                'data': [item['in_progress'] for item in user_tasks]
            },
            {
                'label': 'Pending',
                'data': [item['pending'] for item in user_tasks]
            }
        ]
    }
    
    # Calculate overall completion rate
    total_tasks = all_tasks.count()
    completed_tasks = all_tasks.filter(status='completed').count()
    completion_rate = (completed_tasks / total_tasks * 100) if total_tasks > 0 else 0
    
    # Get recent task activity
    recent_activities = ActivityLog.objects.filter(
        activity_type__in=['task_created', 'task_updated', 'task_completed']
    ).order_by('-timestamp')[:10]
    
    context = {
        'status_data': json.dumps(status_data),
        'completion_data': json.dumps(completion_data),
        'user_data': json.dumps(user_data),
        'completion_rate': round(completion_rate, 1),
        'total_tasks': total_tasks,
        'completed_tasks': completed_tasks,
        'recent_activities': recent_activities
    }
    
    return render(request, 'admin/task_analytics.html', context)

@login_required
def update_task_status(request, task_id):
    if request.method == 'POST':
        try:
            task = get_object_or_404(Goal, id=task_id)
            new_status = request.POST.get('status')
            new_progress = request.POST.get('progress')
            
            # Validate status
            valid_statuses = ['pending', 'in_progress', 'completed', 'missed']
            if new_status not in valid_statuses:
                return JsonResponse({
                    'success': False,
                    'error': 'Invalid status value'
                })
            
            # Validate progress
            try:
                progress = int(new_progress) if new_progress else task.progress
                if not 0 <= progress <= 100:
                    return JsonResponse({
                        'success': False,
                        'error': 'Progress must be between 0 and 100'
                    })
            except ValueError:
                return JsonResponse({
                    'success': False,
                    'error': 'Invalid progress value'
                })
            
            # Update task
            task.status = new_status
            task.progress = progress
            if new_status == 'completed':
                task.completed = True
            task.save()
            
            # Log the activity
            ActivityLog.objects.create(
                user=request.user,
                activity_type='task_updated',
                description=f'Updated task "{task.title}" status to {new_status} with {progress}% progress'
            )
            
            return JsonResponse({
                'success': True,
                'message': 'Task updated successfully',
                'task': {
                    'id': task.id,
                    'status': task.status,
                    'progress': task.progress,
                    'completed': task.completed
                }
            })
            
        except Goal.DoesNotExist:
            return JsonResponse({
                'success': False,
                'error': 'Task not found'
            })
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': str(e)
            })
    
    return JsonResponse({
        'success': False,
        'error': 'Invalid request method'
    })

@login_required
def manage_checkpoints(request, task_id):
    if request.user.user_type != UserTypes.SUPERADMIN:
        messages.error(request, "You don't have permission to manage checkpoints.")
        return redirect('task_detail', task_id=task_id)
    
    task = get_object_or_404(Goal, id=task_id)
    
    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'add_checkpoint':
            title = request.POST.get('title')
            description = request.POST.get('description')
            progress_value = request.POST.get('progress_value')
            
            if title and description and progress_value:
                try:
                    progress_value = int(progress_value)
                    if 0 <= progress_value <= 100:
                        TaskCheckpoint.objects.create(
                            task=task,
                            title=title,
                            description=description,
                            progress_value=progress_value
                        )
                        messages.success(request, 'Checkpoint added successfully!')
                    else:
                        messages.error(request, 'Progress value must be between 0 and 100.')
                except ValueError:
                    messages.error(request, 'Invalid progress value.')
            else:
                messages.error(request, 'All fields are required.')
                
        elif action == 'delete_checkpoint':
            checkpoint_id = request.POST.get('checkpoint_id')
            checkpoint = get_object_or_404(TaskCheckpoint, id=checkpoint_id, task=task)
            checkpoint.delete()
            messages.success(request, 'Checkpoint deleted successfully!')
            
        elif action == 'edit_checkpoint':
            checkpoint_id = request.POST.get('checkpoint_id')
            checkpoint = get_object_or_404(TaskCheckpoint, id=checkpoint_id, task=task)
            
            checkpoint.title = request.POST.get('title')
            checkpoint.description = request.POST.get('description')
            progress_value = request.POST.get('progress_value')
            
            try:
                progress_value = int(progress_value)
                if 0 <= progress_value <= 100:
                    checkpoint.progress_value = progress_value
                    checkpoint.save()
                    messages.success(request, 'Checkpoint updated successfully!')
                else:
                    messages.error(request, 'Progress value must be between 0 and 100.')
            except ValueError:
                messages.error(request, 'Invalid progress value.')
        
        return redirect('manage_checkpoints', task_id=task.id)
    
    context = {
        'task': task,
        'checkpoints': task.checkpoints.all().order_by('created_at')
    }
    return render(request, 'workspace/manage_checkpoints.html', context)

@login_required
def submit_task(request, task_id):
    task = get_object_or_404(Goal, id=task_id)
    
    # Check if user has permission to submit this task
    if task.assigned_to != request.user:
        messages.error(request, "You don't have permission to submit this task.")
        return redirect('user_login')
    
    if request.method == 'POST':
        # Get form data
        completion_notes = request.POST.get('completion_notes')
        supporting_document = request.FILES.get('supporting_document')
        
        # Update task status
        task.status = 'completed'
        task.progress = 100
        task.completed = True
        task.completed_at = timezone.now()
        
        # Save completion notes and document
        if completion_notes:
            task.description += f"\n\nCompletion Notes: {completion_notes}"
        if supporting_document:
            task.attachment = supporting_document
        
        task.save()
        
        # Log the activity
        ActivityLog.objects.create(
            user=request.user,
            action=f'Submitted task: {task.title}',
            details=f'Task completed and submitted with notes: {completion_notes[:100]}...'
        )
        
        # Send email notification to superadmin
        try:
            superadmins = CustomUser.objects.filter(user_type=UserTypes.SUPERADMIN)
            for admin in superadmins:
                if admin.email:
                    subject = f'Task Completed: {task.title}'
                    message = f"""
                    Task '{task.title}' has been completed and submitted by {request.user.get_full_name() or request.user.username}.
                    
                    Completion Notes: {completion_notes}
                    
                    Please review the submission at your earliest convenience.
                    """
                    from_email = settings.DEFAULT_FROM_EMAIL
                    recipient_list = [admin.email]
                    send_mail(subject, message, from_email, recipient_list)
        except Exception as e:
            # Log the error but don't stop the submission process
            print(f"Error sending email notification: {str(e)}")
        
        messages.success(request, "Task submitted successfully!")
        
        # Redirect based on user type
        if request.user.user_type == UserTypes.INTERN:
            return redirect('intern_dashboard', user_id=request.user.id)
        else:
            return redirect('employer_dashboard')
    
    context = {
        'task': task,
    }
    return render(request, 'workspace/submit_task.html', context)