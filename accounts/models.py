from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils.timezone import now
from django.utils import timezone
from django.contrib.auth.models import User

from Employee_Performance_Review_System import settings


class UserTypes(models.TextChoices):
    EMPLOYEE = 'employee', 'Employee'
    EMPLOYER = 'employer', 'Employer'
    MANAGER = 'manager', 'Manager'
    INTERN = 'intern', 'Intern'
    ADMIN = 'admin', 'Admin'
    


class CustomUser(AbstractUser):
    user_type = models.CharField(max_length=10, choices=UserTypes.choices, default="")
    position = models.CharField(max_length=100, blank=True, null=True)

    def __str__(self):
        return self.username
    
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
    
    
#assign Goals
class Goal(models.Model):
    STATUS_CHOICES = [
        ('in_progress', 'In Progress'),
        ('achieved', 'Achieved'),
        ('missed', 'Missed'),
    ]
    title = models.CharField(max_length=100, null=True)
    description = models.TextField()
    status = models.CharField(max_length=100, choices=STATUS_CHOICES)
    progress = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True, null=True)
    deadline = models.DateTimeField(null=True)
    assigned_to = models.ForeignKey(CustomUser,on_delete=models.CASCADE,related_name="goals", null=True)
    completed = models.BooleanField(default=False, null=True)

    def check_deadline(self):
        """Check if the goal's deadline is missed and update the status."""
        if self.deadline and now() > self.deadline:
            self.status = 'missed'
            self.save()

    def __str__(self):
        return self.title if self.title else "Untitled Goal"
    

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

    
