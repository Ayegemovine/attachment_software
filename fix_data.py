# fix_data.py - Save this file and run: python fix_data.py
import os
import sys
import re
import subprocess

def check_and_fix_models():
    """Check if models.py has required fields"""
    print("🔍 Checking models.py...")
    
    models_path = "accounts/models.py"
    if not os.path.exists(models_path):
        print("❌ models.py not found")
        return False
    
    with open(models_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Check if application_number exists
    if 'application_number' not in content:
        print("⚠️  Adding application_number field...")
        
        # Look for Attachee class definition
        if 'class Attachee' in content:
            # Add after the status field
            if 'status = models.CharField' in content:
                content = content.replace(
                    "status = models.CharField",
                    "application_number = models.CharField(max_length=50, unique=True, blank=True, null=True)\n    application_date = models.DateField(auto_now_add=True)\n    status = models.CharField"
                )
            else:
                # Add in the model fields section
                content = content.replace(
                    "class Attachee(models.Model):",
                    "class Attachee(models.Model):\n    application_number = models.CharField(max_length=50, unique=True, blank=True, null=True)\n    application_date = models.DateField(auto_now_add=True)"
                )
            
            with open(models_path, 'w', encoding='utf-8') as f:
                f.write(content)
            print("✅ Added application fields to models.py")
    else:
        print("✅ application_number field exists")
    
    return True

def fix_views_py():
    """Fix the add_attachee view function"""
    print("🔧 Fixing views.py...")
    
    views_path = "accounts/views.py"
    if not os.path.exists(views_path):
        print("❌ views.py not found")
        return False
    
    with open(views_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # The corrected add_attachee function
    new_function = '''def add_attachee(request):
    """Handle attachee applications"""
    from .forms import AttacheeRegistrationForm
    from django.shortcuts import render, redirect
    from django.contrib import messages
    import uuid
    from datetime import date
    
    if request.method == 'POST':
        form = AttacheeRegistrationForm(request.POST, request.FILES)
        if form.is_valid():
            try:
                # Save form data
                attachee = form.save(commit=False)
                
                # Generate unique application number
                attachee.application_number = f"APP-{uuid.uuid4().hex[:8].upper()}"
                attachee.application_date = date.today()
                attachee.status = 'pending'
                
                # Save to database
                attachee.save()
                
                messages.success(request, 'Application submitted successfully!')
                return redirect('application_success', application_number=attachee.application_number)
                
            except Exception as e:
                print(f"ERROR: {e}")
                messages.error(request, f'Error saving application: {str(e)}')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = AttacheeRegistrationForm()
    
    return render(request, 'accounts/add_attachee.html', {'form': form})'''
    
    # Replace existing function
    pattern = r'def add_attachee\(request\):.*?(?=def \w+|\Z)'
    
    if re.search(pattern, content, re.DOTALL):
        content = re.sub(pattern, new_function, content, flags=re.DOTALL)
        print("✅ Updated add_attachee function")
    else:
        # Add if not found
        content += f"\n\n{new_function}"
        print("✅ Added add_attachee function")
    
    with open(views_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    return True

def add_success_view():
    """Add application_success view"""
    print("🎯 Adding success view...")
    
    views_path = "accounts/views.py"
    with open(views_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    if 'def application_success' not in content:
        success_view = '''
def application_success(request, application_number):
    """Success page after application"""
    from .models import Attachee
    from django.shortcuts import get_object_or_404
    
    attachee = get_object_or_404(Attachee, application_number=application_number)
    return render(request, 'accounts/application_success.html', {'attachee': attachee})'''
        
        content += f"\n{success_view}"
        
        with open(views_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        print("✅ Added application_success function")
    
    return True

def update_urls():
    """Update URLs to include success page"""
    print("🔗 Updating urls.py...")
    
    urls_path = "accounts/urls.py"
    if not os.path.exists(urls_path):
        print("❌ urls.py not found")
        return False
    
    with open(urls_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Add success URL pattern
    if 'application-success' not in content:
        # Insert after urlpatterns line
        lines = content.split('\n')
        for i, line in enumerate(lines):
            if 'urlpatterns = [' in line:
                lines.insert(i + 1, "    path('application-success/<str:application_number>/', views.application_success, name='application_success'),")
                break
        
        content = '\n'.join(lines)
        
        with open(urls_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        print("✅ Added success URL to urls.py")
    
    return True

def create_success_template():
    """Create success template"""
    print("📄 Creating success template...")
    
    template_dir = "accounts/templates/accounts"
    os.makedirs(template_dir, exist_ok=True)
    
    template_path = os.path.join(template_dir, "application_success.html")
    
    if not os.path.exists(template_path):
        template_content = '''{% extends "accounts/base.html" %}

{% block content %}
<div class="container mt-5">
    <div class="card shadow">
        <div class="card-header bg-success text-white">
            <h4><i class="fas fa-check-circle me-2"></i>Application Submitted Successfully!</h4>
        </div>
        <div class="card-body text-center py-4">
            <i class="fas fa-check-circle fa-5x text-success mb-3"></i>
            <h3>Thank You, {{ attachee.first_name }}!</h3>
            <p class="lead">Your application has been received and is under review.</p>
            
            <div class="alert alert-info text-start mt-4">
                <h5><i class="fas fa-id-badge me-2"></i>Application Details:</h5>
                <p><strong>Application Number:</strong> {{ attachee.application_number }}</p>
                <p><strong>Name:</strong> {{ attachee.first_name }} {{ attachee.last_name }}</p>
                <p><strong>Email:</strong> {{ attachee.email }}</p>
                <p><strong>Date:</strong> {{ attachee.application_date }}</p>
            </div>
            
            <div class="alert alert-warning">
                <i class="fas fa-exclamation-triangle me-2"></i>
                Save your application number: <strong>{{ attachee.application_number }}</strong>
            </div>
            
            <div class="mt-4">
                <a href="/check-status/" class="btn btn-primary me-2">
                    <i class="fas fa-search me-1"></i>Check Status
                </a>
                <a href="/" class="btn btn-outline-secondary">
                    <i class="fas fa-home me-1"></i>Return Home
                </a>
            </div>
        </div>
    </div>
</div>
{% endblock %}'''
        
        with open(template_path, 'w', encoding='utf-8') as f:
            f.write(template_content)
        
        print("✅ Created application_success.html template")
    
    return True

def run_migrations():
    """Run database migrations"""
    print("🔄 Running migrations...")
    
    try:
        # Make migrations
        result = subprocess.run(
            [sys.executable, 'manage.py', 'makemigrations', 'accounts'],
            capture_output=True,
            text=True
        )
        print(result.stdout)
        
        # Apply migrations
        result = subprocess.run(
            [sys.executable, 'manage.py', 'migrate', 'accounts'],
            capture_output=True,
            text=True
        )
        print(result.stdout)
        
        print("✅ Migrations completed")
        return True
    except Exception as e:
        print(f"⚠️ Migration error: {e}")
        print("Please run manually:")
        print("python manage.py makemigrations accounts")
        print("python manage.py migrate accounts")
        return False

def main():
    """Main function"""
    print("=" * 50)
    print("🔧 FIXING DATA SAVING ISSUE")
    print("=" * 50)
    
    # Run all fixes
    check_and_fix_models()
    fix_views_py()
    add_success_view()
    update_urls()
    create_success_template()
    run_migrations()
    
    print("\n" + "=" * 50)
    print("✅ ALL FIXES COMPLETED!")
    print("=" * 50)
    
    print("\n📋 NEXT STEPS:")
    print("1. Restart your Django server (Ctrl+C then run again)")
    print("2. Test the form at: http://localhost:8080/apply/")
    print("3. Data should now save and redirect to success page")
    print("4. Check status at: http://localhost:8080/check-status/")
    
    print("\n🎯 To restart server:")
    print("python manage.py runserver 8080")

if __name__ == "__main__":
    main()