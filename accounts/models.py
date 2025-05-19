from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils.timezone import now
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils.translation import gettext_lazy as _
from django.utils import timezone

from Employee_Performance_Review_System import settings


class UserTypes(models.TextChoices):
    EMPLOYEE = 'employee', _('Employee')
    EMPLOYER = 'employer', _('Employer')
    INTERN = 'intern', _('Intern')
    SUPERADMIN = 'superadmin', _('Superadmin')
    


class CustomUser(AbstractUser):
    user_type = models.CharField(
        max_length=10,
        choices=UserTypes.choices,
        default=UserTypes.EMPLOYEE,
        verbose_name=_('User Type')
    )
    position = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        verbose_name=_('Position')
    )
    profile_picture = models.ImageField(
        upload_to='profile_pictures/',
        null=True,
        blank=True,
        verbose_name=_('Profile Picture')
    )
    phone_number = models.CharField(
        max_length=15,
        blank=True,
        null=True,
        verbose_name=_('Phone Number')
    )
    department = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        verbose_name=_('Department')
    )

    class Meta:
        verbose_name = _('User')
        verbose_name_plural = _('Users')

    def __str__(self):
        return self.username
    
class Attend(models.Model):
    attender = models.ForeignKey(
        'CustomUser',
        on_delete=models.CASCADE,
        verbose_name=_('Attender')
    )
    datetime = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_('Date and Time')
    )
    status = models.CharField(
        max_length=20,
        choices=[
            ('present', _('Present')),
            ('late', _('Late')),
            ('absent', _('Absent'))
        ],
        default='present',
        verbose_name=_('Status')
    )

    class Meta:
        verbose_name = _('Attendance')
        verbose_name_plural = _('Attendance Records')
        ordering = ['-datetime']

    def __str__(self):
        return f"{self.attender.username} - {self.datetime.strftime('%Y-%m-%d %H:%M')}"



class PerformanceReview(models.Model):
    user = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        verbose_name=_('Employee')
    )
    date = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_('Review Date')
    )
    productivity_score = models.IntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        verbose_name=_('Productivity Score')
    )
    punctuality_score = models.IntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        verbose_name=_('Punctuality Score')
    )
    collaboration_score = models.IntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        verbose_name=_('Collaboration Score')
    )
    goals = models.TextField(verbose_name=_('Goals'))
    feedback = models.TextField(verbose_name=_('Feedback'))
    reviewer = models.ForeignKey(
        CustomUser,
        on_delete=models.SET_NULL,
        null=True,
        related_name='performance_reviews_given',
        verbose_name=_('Reviewer')
    )

    class Meta:
        verbose_name = _('Performance Review')
        verbose_name_plural = _('Performance Reviews')
        ordering = ['-date']

    def __str__(self):
        return f"Review for {self.user.username} on {self.date.strftime('%Y-%m-%d')}"
    
    @property
    def average_score(self):
        return (self.productivity_score + self.punctuality_score + self.collaboration_score) / 3

#assign Goals
class Goal(models.Model):
    STATUS_CHOICES = [
        ('in_progress', _('In Progress')),
        ('achieved', _('Achieved')),
        ('missed', _('Missed')),
    ]
    title = models.CharField(
        max_length=100,
        verbose_name=_('Title')
    )
    description = models.TextField(verbose_name=_('Description'))
    status = models.CharField(
        max_length=100,
        choices=STATUS_CHOICES,
        default='in_progress',
        verbose_name=_('Status')
    )
    progress = models.PositiveIntegerField(
        default=0,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        verbose_name=_('Progress')
    )
    created_at = models.DateTimeField(
        default=timezone.now,  # Set default to timezone.now
        null=True,  # Temporarily allow null
        blank=True,  # Temporarily allow blank
        verbose_name=_('Created At')
    )
    deadline = models.DateTimeField(
        null=True,
        verbose_name=_('Deadline')
    )
    assigned_to = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name="goals",
        verbose_name=_('Assigned To'),
        null=True,  # Allow null temporarily
        blank=True  # Allow blank temporarily
    )
    completed = models.BooleanField(
        default=False,
        verbose_name=_('Completed')
    )
    priority = models.CharField(
        max_length=20,
        choices=[
            ('low', _('Low')),
            ('medium', _('Medium')),
            ('high', _('High'))
        ],
        default='medium',
        verbose_name=_('Priority')
    )

    class Meta:
        verbose_name = _('Goal')
        verbose_name_plural = _('Goals')
        ordering = ['-created_at']

    def check_deadline(self):
        """Check if the goal's deadline is missed and update the status."""
        if self.deadline and now() > self.deadline:
            self.status = 'missed'
            self.save()

    def __str__(self):
        return self.title if self.title else "Untitled Goal"
    

class ReviewScheduling(models.Model):
    user = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        verbose_name=_('Employee')
    )
    review_title = models.CharField(
        max_length=100,
        verbose_name=_('Review Title')
    )
    review_date = models.DateField(verbose_name=_('Review Date'))
    review_time = models.TimeField(verbose_name=_('Review Time'))
    status = models.CharField(
        max_length=20,
        choices=[
            ('scheduled', _('Scheduled')),
            ('completed', _('Completed')),
            ('cancelled', _('Cancelled'))
        ],
        default='scheduled',
        verbose_name=_('Status')
    )
    notes = models.TextField(
        blank=True,
        null=True,
        verbose_name=_('Notes')
    )

    class Meta:
        verbose_name = _('Review Schedule')
        verbose_name_plural = _('Review Schedules')
        ordering = ['review_date', 'review_time']

    def __str__(self):
        return f"{self.review_title} - {self.review_date.strftime('%Y-%m-%d')} at {self.review_time.strftime('%H:%M')}"


#review  
class Review(models.Model):
    reviewer = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name='reviews_given',
        verbose_name=_('Reviewer')
    )
    employee = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name='reviews_received',
        verbose_name=_('Employee')
    )
    review_date = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_('Review Date')
    )
    feedback = models.TextField(verbose_name=_('Feedback'))
    rating = models.IntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        verbose_name=_('Rating')
    )
    strengths = models.TextField(
        blank=True,
        null=True,
        verbose_name=_('Strengths')
    )
    areas_for_improvement = models.TextField(
        blank=True,
        null=True,
        verbose_name=_('Areas for Improvement')
    )

    class Meta:
        verbose_name = _('Review')
        verbose_name_plural = _('Reviews')
        ordering = ['-review_date']

    def __str__(self):
        return f"Review by {self.reviewer.username} for {self.employee.username}"


# Chat message model for chat system
class ChatMessage(models.Model):
    sender = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name='sent_messages',
        verbose_name=_('Sender')
    )
    receiver = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name='received_messages',
        verbose_name=_('Receiver')
    )
    message = models.TextField(verbose_name=_('Message'))
    timestamp = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_('Timestamp')
    )
    is_read = models.BooleanField(
        default=False,
        verbose_name=_('Is Read')
    )

    class Meta:
        verbose_name = _('Chat Message')
        verbose_name_plural = _('Chat Messages')
        ordering = ['timestamp']

    def __str__(self):
        return f"From {self.sender.username} to {self.receiver.username} at {self.timestamp.strftime('%Y-%m-%d %H:%M:%S')}"

class ActivityLog(models.Model):
    user = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        verbose_name=_('User')
    )
    action = models.CharField(
        max_length=255,
        verbose_name=_('Action')
    )
    timestamp = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_('Timestamp')
    )
    ip_address = models.GenericIPAddressField(
        null=True,
        blank=True,
        verbose_name=_('IP Address')
    )
    user_agent = models.TextField(
        null=True,
        blank=True,
        verbose_name=_('User Agent')
    )

    class Meta:
        verbose_name = _('Activity Log')
        verbose_name_plural = _('Activity Logs')
        ordering = ['-timestamp']

    def __str__(self):
        return f"{self.user.username} - {self.action} at {self.timestamp.strftime('%Y-%m-%d %H:%M:%S')}"
        
    
