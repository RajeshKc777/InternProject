from django.shortcuts import render, redirect
from .models import CustomUser, UserTypes, PerformanceReview, Goal, ReviewScheduling, Review
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.shortcuts import get_object_or_404
from datetime import datetime, timezone
from .models import CustomUser
from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from .models import Attend
from django.utils import timezone

from django.shortcuts import render


# Create your views here.
def user_register(request):
    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")
        confirm_password = request.POST.get("password2")
        email = request.POST.get("email")
        user_type = request.POST.get('user_type')

        if password != confirm_password:
            messages.error(request, "password need to be same")
            return redirect('user_register')
        else:

            if CustomUser.objects.filter(username=username).exists():
                messages.error(request, "username already existed!")
                return redirect('user_register')
            elif CustomUser.objects.filter(email=email).exists():
                messages.error(request, "email already taken")
                return redirect('user_register')
            else:
                # Create a new user
                user = CustomUser(
                    username=username,
                    email=email,
                    user_type=user_type
                )
                user.set_password(password)
                user.save()
                messages.success(request, "Account created successfully")
                return redirect('user_login')  

    return render(request, "registration/register.html")

def user_login(request):
    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")
        
        user = authenticate(request, username=username, password=password)

        if user is not None:
            print(user.user_type)

            login(request, user)
            # Redirect based on user type
            if user.user_type == UserTypes.EMPLOYER:
                return redirect('employer_dashboard')  
            elif user.user_type == UserTypes.EMPLOYEE:
                return redirect('employee_dashboard')
            elif user.user_type == UserTypes.MANAGER:
                return redirect('manager_dashboard')   
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




# manager 
def manager_dashboard(request):

    employees = CustomUser.objects.filter(user_type=UserTypes.EMPLOYER)
    interns = CustomUser.objects.filter(user_type=UserTypes.INTERN)
    # print(request.user.user_type)
    context = {
        'employees': employees,
        'interns': interns,
        'user': request.user

    }
    return render(request, "manager/manager_dashboard.html", context)

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
            Goal.objects.create(
                title=title,
                description=description,
                status='in_progress',
                progress=0,
                deadline=deadline if deadline else None  # Set deadline if provided
            )
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
def intern_dashboard(request, user_id):
    user = get_object_or_404(CustomUser, id=user_id, user_type=UserTypes.INTERN)
    if request.user != user:
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

def assign_goals(request):
    users = CustomUser.objects.filter(user_type__in=[UserTypes.INTERN, UserTypes.EMPLOYER])  # Adjust as needed
    if request.method == 'POST':
        title = request.POST.get('title')
        description = request.POST.get('description')
        deadline = request.POST.get('deadline')
        assigned_to_id = request.POST.get('assigned_to')
        assigned_to = CustomUser.objects.get(id=assigned_to_id)

        # Create and save the goal
        goal = Goal.objects.create(
            title=title,
            description=description,
            deadline=deadline,
            assigned_to=assigned_to
        )
        goal.save()


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
                attended_datetime = str(timezone.now())[:10]
                print(attended_datetime)
            except:
                pass

            attended_today = Attend.objects.filter(attender=request.user, datetime__startswith=attended_datetime)
            
            if str(attended_today)[10:] == "[]>":
                status = 3

            else:
                status = 2

            if status == 3:
                attend_object = Attend(attender=request.user)
                attend_object.save()
                status= 1

        else: 
            status = 0
         # Get the attendance records for the logged-in user
         
    if request.user.is_authenticated:
        attendance_records = Attend.objects.filter(attender=request.user).order_by('-datetime')

    return render(request, "attendance/attendance.html", {'status': status ,'attendance_records': attendance_records})


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


from django.contrib.auth.decorators import login_required
from django.contrib.auth import update_session_auth_hash

@login_required
def change_password(request):
    if request.method == "POST":
        current_password = request.POST.get("current_password")
        new_password = request.POST.get("new_password")
        confirm_password = request.POST.get("confirm_password")

        if not request.user.check_password(current_password):
            messages.error(request, "Current password is incorrect.")
        elif new_password != confirm_password:
            messages.error(request, "New passwords do not match.")
        else:
            request.user.set_password(new_password)
            request.user.save()
            update_session_auth_hash(request, request.user)  # Keep user logged in
            messages.success(request, "Password changed successfully.")
            return redirect("change_password")

    return render(request, "registration/change_password.html")
