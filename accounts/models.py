from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils.timezone import now
from django.utils import timezone
from django.contrib.auth.models import User

from Employee_Performance_Review_System import settings


class UserTypes(models.TextChoices):
    EMPLOYEE = 'employee', 'Employee'
    EMPLOYER = 'employer', 'Employer'
    INTERN = 'intern', 'Intern'
    SUPERADMIN = 'superadmin', 'Superadmin'
    ADMIN = 'admin', 'Admin'  # Added ADMIN type


class CustomUser(AbstractUser):
    user_type = models.CharField(max_length=10, choices=UserTypes.choices, default="")
    position = models.CharField(max_length=100, blank=True, null=True)

    def __str__(self):
        return self.username


class Workspace(models.Model):
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE, related_name='workspace')
    name = models.CharField(max_length=100, default="My Workspace")
    description = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.user.username}'s Workspace"

    def get_tasks(self):
        return self.goals.filter(assigned_to=self.user)

    def get_completed_tasks(self):
        return self.goals.filter(assigned_to=self.user, status='achieved')

    def get_in_progress_tasks(self):
        return self.goals.filter(assigned_to=self.user, status='in_progress')

    def get_missed_tasks(self):
        return self.goals.filter(assigned_to=self.user, status='missed')


class Attend(models.Model):
    attender = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    datetime = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return str(self.attender.username) + " " + str(self.datetime)[:19]


class PerformanceReview(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)  # employee or intern
    date = models.DateTimeField(auto_now_add=True)
    productivity_score = models.IntegerField()
    punctuality_score = models.IntegerField()
    collaboration_score = models.IntegerField()
    goals = models.TextField()
    feedback = models.TextField()

    def __str__(self):
        return f"Review for {self.user.username} on {self.date}"


class Goal(models.Model):
    STATUS_CHOICES = [
        ('in_progress', 'In Progress'),
        ('achieved', 'Achieved'),
        ('missed', 'Missed'),
    ]
    PRIORITY_CHOICES = [
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
    ]
    title = models.CharField(max_length=100, null=True)
    description = models.TextField()
    status = models.CharField(max_length=100, choices=STATUS_CHOICES)
    progress = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True, null=True)
    deadline = models.DateTimeField(null=True)
    assigned_to = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name="goals", null=True)
    workspace = models.ForeignKey(Workspace, on_delete=models.CASCADE, related_name="goals", null=True)
    completed = models.BooleanField(default=False, null=True)
    priority = models.CharField(max_length=10, choices=PRIORITY_CHOICES, default='medium')
    attachment = models.FileField(upload_to='task_attachments/', null=True, blank=True)
    tags = models.CharField(max_length=255, blank=True, null=True, help_text="Comma-separated tags for the task")

    def check_deadline(self):
        """Check if the goal's deadline is missed and update the status."""
        if self.deadline and now() > self.deadline:
            self.status = 'missed'
            self.save()

    def __str__(self):
        return self.title if self.title else "Untitled Goal"

    def save(self, *args, **kwargs):
        # If workspace is not set and assigned_to is set, create/get workspace
        if not self.workspace and self.assigned_to:
            workspace, created = Workspace.objects.get_or_create(user=self.assigned_to)
            self.workspace = workspace
        super().save(*args, **kwargs)


class TaskComment(models.Model):
    goal = models.ForeignKey(Goal, on_delete=models.CASCADE, related_name='comments')
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    comment = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Comment by {self.user.username} on {self.goal.title}"
    

class ReviewScheduling(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    review_title = models.CharField(max_length=100)
    review_date = models.DateField()
    review_time = models.TimeField()

    def __str__(self):
        return f"{self.review_title} - {self.review_date.strftime('%Y-%m-%d')} at {self.review_time.strftime('%H:%M')}"


#review  
class Review(models.Model):
    reviewer = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='reviews_given')
    employee = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='reviews_received')
    review_date = models.DateTimeField(auto_now_add=True)
    feedback = models.TextField()
    rating = models.IntegerField()

    def __str__(self):
        return f"Review by {self.reviewer.username} for {self.employee.username}"


# Chat message model for chat system
class ChatMessage(models.Model):
    sender = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='sent_messages')
    receiver = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='received_messages')
    message = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"From {self.sender.username} to {self.receiver.username} at {self.timestamp.strftime('%Y-%m-%d %H:%M:%S')}"

class ActivityLog(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    action = models.CharField(max_length=255)
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} - {self.action} at {self.timestamp.strftime('%Y-%m-%d %H:%M:%S')}"
        
    
