from django.contrib.auth import views as auth_views
from django.urls import path
from . import views

urlpatterns = [
    # Authentication Routes
    path('logout/', auth_views.LogoutView.as_view(next_page='home'), name='logout'),
    path('login/', auth_views.LoginView.as_view(template_name='accounts/login.html'), name='login'),
    
    # Core Application Routes
    path('', views.home, name='home'),
    
    # FIXED: Name changed from 'apply' to 'add_attachee' to match your templates
    path('apply/', views.add_attachee, name='add_attachee'), 
    
    path('application-success/<str:application_number>/', views.application_success, name='application_success'),
    path('check-status/', views.check_status, name='check_status'),
    path('dashboard/', views.dashboard, name='dashboard'),
    
    # Dashboard Data Tools (Excel/CSV Utilities)
    path('dashboard/export/', views.export_attachees, name='export_attachees'),
    path('dashboard/import/', views.import_attachees, name='import_attachees'),
    
    # Dashboard Modal Status & Notes Update Logic
    # This path connects the AJAX/Form from the dashboard modal to the database
    path('update-status/<int:pk>/', views.update_status, name='update_status'),
    
    # Legacy Admin Action Paths (Individual button actions)
    path('approve/<int:attachee_id>/', views.approve_student, name='approve_student'),
    path('reject/<int:attachee_id>/', views.reject_student, name='reject_student'),
    
    # Analytics and Feedback Systems
    path('analytics/', views.university_analytics, name='university_analytics'),
    path('submit-feedback/<int:attachee_id>/', views.submit_feedback, name='submit_feedback'),
    
    # Branded Document Downloads (HR Documents)
    path('download-pass/<int:attachee_id>/', views.download_gate_pass, name='download_gate_pass'),
    path('download-completion/<int:attachee_id>/', views.download_completion_letter, name='download_completion_letter'),
    path('recommendation/<int:attachee_id>/', views.download_recommendation_letter, name='download_recommendation_letter'),

    # --- NEW: Attachment ID Card Route ---
    # This maps the "Download ID Card" buttons to the generation function in views.py
    path('download-id/<int:attachee_id>/', views.download_id_card, name='download_id_card'),
]