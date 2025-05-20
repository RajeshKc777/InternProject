from django import forms
from .models import Goal, TaskComment

class TaskForm(forms.ModelForm):
    class Meta:
        model = Goal
        fields = ['title', 'description', 'assigned_to', 'deadline', 'priority', 'attachment', 'status', 'progress', 'completed']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control'}),
            'assigned_to': forms.Select(attrs={'class': 'form-control'}),
            'deadline': forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}),
            'priority': forms.Select(attrs={'class': 'form-control'}),
            'attachment': forms.ClearableFileInput(attrs={'class': 'form-control'}),
            'status': forms.Select(attrs={'class': 'form-control'}),
            'progress': forms.NumberInput(attrs={'class': 'form-control', 'min': 0, 'max': 100}),
            'completed': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

class TaskCommentForm(forms.ModelForm):
    class Meta:
        model = TaskComment
        fields = ['comment']
        widgets = {
            'comment': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Add a comment...'}),
        }
