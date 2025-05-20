from django.contrib import admin
from django.urls import path, include
from accounts import views


urlpatterns = [
    path('', views.user_login, name="user_login"),
    path('register/', views.user_register, name="user_register"),
    path('superadmin/', views.superadmin_dashboard, name="superadmin_dashboard"),
    path('superadmin/users/', views.superadmin_users_list, name='superadmin_users_list'),
    path('superadmin/users/add/', views.superadmin_user_add, name='superadmin_user_add'),
    path('superadmin/users/<int:user_id>/edit/', views.superadmin_user_edit, name='superadmin_user_edit'),
    path('superadmin/users/<int:user_id>/delete/', views.superadmin_user_delete, name='superadmin_user_delete'),
    path('work_desc/<int:user_id>/', views.work_desc, name='work_desc'),
    path('performance_details/<int:review_id>/', views.performance_details, name='performance_details'),
    path('reviews/<int:user_id>/', views.allReview, name='all_reviews'),
    path('assign_goal/', views.assign_goal, name='assign_goal'),
    path('upcoming_reviews/', views.UpCommingReview, name='UpCommingReview'),
    path('employer/', views.employer_dashboard, name="employer_dashboard"),
    path('intern/<int:user_id>/', views.intern_dashboard, name="intern_dashboard"),
    path('intern_performance/<int:review_id>/', views.intern_performance_details, name='intern_performance_details'),
    path('goals/', views.goals, name="goals"),
    path('goals_history/', views.goals_history, name="goals_history"),
    path('self_assessment/', views.Self_Assessment, name="Self_Assessment"),
    path('chat/<int:user_id>/', views.chat_view, name='chat'),
    path('send_message/', views.send_message, name='send_message'),
    path('user_list/<str:role>/', views.user_list_by_role, name='user_list_by_role'),
    path('users/', views.users_list, name='users_list'),
    path('tasks/', views.tasks_list, name='tasks_list'),
    path('tasks/create/', views.task_create, name='task_create'),
    path('tasks/<int:task_id>/', views.task_detail, name='task_detail'),
    path('attendance/', views.attendance_list, name='attendance'),
    path('attendance/view/', views.attendance_view, name='attendance_view'),
    path('attendance/admin/', views.admin_attendance_view, name='admin_attendance_view'),
    path('notifications/', views.notifications_list, name='notifications_list'),
    path('edit_review/<int:review_id>/edit/', views.edit_review, name='edit_review'),
    path('logout/', views.logout_view, name='logout'),
    path('profile/', views.user_profile, name='user_profile'),

    # Add Django auth urls for password reset and other auth views
    path('accounts/', include('django.contrib.auth.urls')),

    path('workspace/', views.personal_workspace, name='personal_workspace'),
    path('workspace/update/', views.update_workspace, name='update_workspace'),
    path('workspace/tasks/', views.task_management, name='task_management'),
    path('workspace/task/create/', views.create_task, name='create_task'),
    path('workspace/task/<int:task_id>/', views.task_detail, name='task_detail'),
    path('workspace/task/<int:task_id>/edit/', views.edit_task, name='edit_task'),
    path('workspace/task/<int:task_id>/delete/', views.delete_task, name='delete_task'),
    path('workspace/task/<int:task_id>/comment/', views.add_comment, name='add_comment'),
]
