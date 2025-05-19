from django.shortcuts import render, redirect, get_object_or_404
from .models import CustomUser, UserTypes, PerformanceReview, Goal, ReviewScheduling, Review, ChatMessage, ActivityLog, Attend
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.core.mail import send_mail
from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.db import models
from django.contrib.auth.models import User
from .forms import UserProfileForm, PasswordChangeForm
import json
from datetime import datetime, timedelta
from django.db.models import Count

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
            elif user.user_type == UserTypes.EMPLOYEE:
                return redirect('employee_dashboard')
            elif user.user_type == UserTypes.INTERN:
                return redirect('intern_dashboard')
        else:
            if CustomUser.objects.filter(username=username).exists():
                messages.error(request, "Invalid password.")
            else:
                messages.error(request, "Invalid username.")
            return redirect('user_login')

    return render(request, "registration/login.html")

@login_required
def chat_view(request, user_id):
    other_user = get_object_or_404(CustomUser, id=user_id)
    if request.user == other_user:
        messages.error(request, "Cannot chat with yourself.")
        return redirect('user_list')
    
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
        return JsonResponse({'status': 'success', 'message': 'Message sent.'})
    return JsonResponse({'status': 'fail', 'message': 'Invalid request.'})

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

def user_register(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        email = request.POST.get('email')
        password = request.POST.get('password')
        password2 = request.POST.get('password2')
        role = request.POST.get('role')

        # Validate passwords match
        if password != password2:
            messages.error(request, "Passwords do not match.")
            return redirect('user_register')

        # Validate role selection
        valid_roles = [choice[0] for choice in UserTypes.choices]
        if role not in valid_roles:
            messages.error(request, "Invalid role selected.")
            return redirect('user_register')

        try:
            # Create user
            user = CustomUser.objects.create_user(username=username, email=email, password=password)
            user.user_type = role
            user.save()
            messages.success(request, 'Registration successful! Please login.')
            return redirect('user_login')

        except Exception as e:
            messages.error(request, f'Registration failed: {str(e)}')
            return redirect('user_register')

    return render(request, 'registration/register.html', {'roles': [choice[0] for choice in UserTypes.choices]})

@login_required
def superadmin_dashboard(request):
    if request.user.user_type != UserTypes.SUPERADMIN:
        return redirect('user_login')

    # Get all users except superadmin
    users = CustomUser.objects.exclude(user_type=UserTypes.SUPERADMIN)
    goals = Goal.objects.all()
    attendance_records = Attend.objects.filter(datetime__gte=timezone.now()-timedelta(days=30))
    performance_reviews = PerformanceReview.objects.all().order_by('-date')[:10]
    notifications = Goal.objects.filter(models.Q(deadline__lte=timezone.now() + timedelta(days=3)) | models.Q(status='missed'))

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
    return render(request, "superadmin/superadmin_dashboard.html", context)

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
        return redirect('user_login')

    if request.method == 'POST':
        username = request.POST.get('username')
        email = request.POST.get('email')
        user_type = request.POST.get('user_type')
        password = request.POST.get('password')
        password2 = request.POST.get('password2')

        if password != password2:
            messages.error(request, "Passwords do not match.")
            return redirect('superadmin_user_add')

        if CustomUser.objects.filter(username=username).exists():
            messages.error(request, "Username already exists.")
            return redirect('superadmin_user_add')

        user = CustomUser.objects.create_user(username=username, email=email, password=password)
        user.user_type = user_type
        user.save()
        messages.success(request, "User added successfully.")
        return redirect('superadmin_users_list')

    context = {
        'user_types': UserTypes.choices,
    }
    return render(request, "superadmin/user_add.html", context)

@login_required
def users_list(request):
    if request.user.user_type != UserTypes.SUPERADMIN:
        return redirect('user_login')

    users = CustomUser.objects.exclude(user_type=UserTypes.SUPERADMIN)
    context = {
        'users': users,
    }
    return render(request, "admin/users_list.html", context)

@login_required
def superadmin_user_delete(request, user_id):
    if request.user.user_type != UserTypes.SUPERADMIN:
        return redirect('user_login')

    user = get_object_or_404(CustomUser, id=user_id)
    user.delete()
    messages.success(request, "User deleted successfully.")
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
    if request.user.user_type != UserTypes.ADMIN:
        return redirect('user_login')

    goals = Goal.objects.all().order_by('deadline')
    context = {
        'goals': goals,
    }
    return render(request, "admin/tasks_list.html", context)

@login_required
def attendance_list(request):
    if request.user.user_type != UserTypes.ADMIN:
        return redirect('user_login')

    attendance_records = Attend.objects.all().order_by('-datetime')[:50]
    context = {
        'attendance_records': attendance_records,
    }
    return render(request, "admin/attendance_list.html", context)

@login_required
def notifications_list(request):
    if request.user.user_type != UserTypes.ADMIN:
        return redirect('user_login')

    upcoming_deadline = timezone.now() + timedelta(days=3)
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
        return redirect('user_login')  # Ensure only employers (employees) access this dashboard
    
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
    return render(request, "employer/employer_dashboard.html", data)

#intern
@login_required
def intern_dashboard(request):
    user = request.user
    if user.user_type != UserTypes.INTERN:
        return redirect('user_login')  # Ensure only the intern can access their dashboard
    
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
    return render(request, "intern/intern_dashboard.html", data)
        
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
            return redirect('intern_dashboard_detail', intern_id=user.id)
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

@login_required
def assign_goals(request):
    if request.user.user_type not in [UserTypes.SUPERADMIN, UserTypes.EMPLOYER]:
        messages.error(request, "You don't have permission to assign goals.")
        return redirect('user_login')

    if request.method == 'POST':
        title = request.POST.get('title')
        description = request.POST.get('description')
        deadline = request.POST.get('deadline')
        assigned_to_id = request.POST.get('assigned_to')

        if not all([title, description, assigned_to_id]):
            messages.error(request, "All fields are required.")
            return redirect('assign_goals')

        try:
            assigned_to = CustomUser.objects.get(id=assigned_to_id)
            
            # Create and save the goal
            goal = Goal.objects.create(
                title=title,
                description=description,
                deadline=datetime.strptime(deadline, "%Y-%m-%d") if deadline else None,
                assigned_to=assigned_to,
                status='in_progress',
                progress=0
            )
            goal.save()

            # Send email notification to assigned user
            if assigned_to.email:
                subject = 'New Goal Assigned'
                message = f'Hello {assigned_to.username},\n\nYou have been assigned a new goal: {title}.\n\nDescription: {description}\nDeadline: {deadline}\n\nPlease check your dashboard for more details.'
                from_email = settings.DEFAULT_FROM_EMAIL if hasattr(settings, 'DEFAULT_FROM_EMAIL') else 'no-reply@example.com'
                recipient_list = [assigned_to.email]
                send_mail(subject, message, from_email, recipient_list)

            messages.success(request, "Goal assigned successfully!")
            return redirect('assign_goals')

        except CustomUser.DoesNotExist:
            messages.error(request, "Selected user does not exist.")
        except Exception as e:
            messages.error(request, f"An error occurred: {str(e)}")
        return redirect('assign_goals')

    # Get all users who can be assigned goals (employees and interns)
    users = CustomUser.objects.filter(user_type__in=[UserTypes.EMPLOYEE, UserTypes.INTERN])
    context = {
        'users': users,
    }
    return render(request, 'manager/assign_goals.html', context)

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

@login_required
def attendance_view(request):
    if request.method == "POST":
        try:
            attended_date = timezone.now().date()
            attended_today = Attend.objects.filter(attender=request.user, datetime__date=attended_date)
            
            if not attended_today.exists():
                attend_object = Attend.objects.create(
                    attender=request.user,
                    datetime=timezone.now(),
                    status='present'
                )
                attend_object.save()
                messages.success(request, "Attendance marked successfully!")
                status = 1  # Attendance marked successfully
            else:
                messages.info(request, "You have already marked your attendance today.")
                status = 2  # Already marked attendance
        except Exception as e:
            messages.error(request, f"An error occurred: {str(e)}")
            status = 0  # Error occurred
    else:
        status = None

    # Get the attendance records for the logged-in user
    attendance_records = Attend.objects.filter(attender=request.user).order_by('-datetime') if request.user.is_authenticated else []

    return render(request, "attendance/attendance.html", {
        'status': status,
        'attendance_records': attendance_records
    })

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

def admin_dashboard(request):
    # Add admin-specific data queries here
    context = {
        'total_users': User.objects.count(),
        'recent_activities': ActivityLog.objects.all().order_by('-timestamp')[:10]
    }
    return render(request, 'accounts/admin_dashboard.html', context)

def logout_view(request):
    """
    Logs out the user and redirects to the login page.
    """
    logout(request)
    messages.success(request, "You have been successfully logged out.")
    return redirect('user_login')

@login_required
def intern_dashboard_detail(request, intern_id):
    user = get_object_or_404(CustomUser, id=intern_id)
    if user.user_type != UserTypes.INTERN:
        return redirect('user_login')
    
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
    return render(request, "intern/intern_dashboard.html", data)