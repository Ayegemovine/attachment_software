from django.contrib.auth import views as auth_views
from django.urls import path
from . import views

urlpatterns = [
    path('logout/', auth_views.LogoutView.as_view(next_page='home'), name='logout'),
    path('login/', auth_views.LoginView.as_view(template_name='accounts/login.html'), name='login'),
    path('', views.home, name='home'),
    path('apply/', views.add_attachee, name='apply'),
    path('application-success/<str:application_number>/', views.application_success, name='application_success'),
    path('check-status/', views.check_status, name='check_status'),
    path('dashboard/', views.dashboard, name='dashboard'),
    
    # Dashboard Data Tools
    path('dashboard/export/', views.export_attachees, name='export_attachees'),
    path('dashboard/import/', views.import_attachees, name='import_attachees'), # Added for CSV Import logic
    
    # Dashboard Modal Status Update Logic
    path('update-status/<int:pk>/', views.update_status, name='update_status'),
    
    # Admin Action Paths
    path('approve/<int:attachee_id>/', views.approve_student, name='approve_student'),
    path('reject/<int:attachee_id>/', views.reject_student, name='reject_student'),
    
    # Analytics and Feedback
    path('analytics/', views.university_analytics, name='university_analytics'),
    path('submit-feedback/<int:attachee_id>/', views.submit_feedback, name='submit_feedback'),
    
    # Branded Document Downloads
    path('download-pass/<int:attachee_id>/', views.download_gate_pass, name='download_gate_pass'),
    path('download-completion/<int:attachee_id>/', views.download_completion_letter, name='download_completion_letter'),
    path('recommendation/<int:attachee_id>/', views.download_recommendation_letter, name='download_recommendation_letter'),
]