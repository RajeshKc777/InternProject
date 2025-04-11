from django.contrib import admin
from django.urls import path
from accounts import views


urlpatterns = [
    path('',views.user_login, name="user_login"),
    path('register/',views.user_register, name="user_register"),


    #manager
    path('manager_dashboard/', views.manager_dashboard, name="manager_dashboard"),
    path('work_desc/<int:user_id>/', views.work_desc, name='work_desc'),
    path('performance_details/<int:review_id>/', views.performance_details, name='performance_details'),
    path('reviews/<int:user_id>', views.allReview, name='all_reviews'),
    path('assign_goal/', views.assign_goal, name='assign_goal'),
    path('UpCommingReview/', views.UpCommingReview, name='UpCommingReview'),

    

    # employer
    path('employer_dashboard/', views.employer_dashboard, name="employer_dashboard"),

    # Intern
    path('intern_dashboard/<int:user_id>/', views.intern_dashboard, name="intern_dashboard"),
    path('intern_performance_details/<int:review_id>/', views.intern_performance_details, name='intern_performance_details'),
    path('goals/', views.goals, name="goals"),
    path('goals_history/', views.goals_history, name="goals_history"),
    path('Self_Assessment/', views.Self_Assessment, name="Self_Assessment"),
    
    # Employees 
    path('employee_dashboard/', views.employee_dashboard, name="employee_dashboard"),
    
    
    path('edit_review/<int:review_id>/edit/', views.edit_review, name='edit_review'),
    path('logout/', views.logout_view, name='logout'),  # Logout URL

   

    path('attendance/', views.attendance_view, name="attendance")
    

]