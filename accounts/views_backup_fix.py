from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from .models import Attachee
from .forms import AttacheeRegistrationForm
import uuid
from datetime import date

def home(request):
    return render(request, 'accounts/home.html')

def add_attachee(request):
    if request.method == 'POST':
        form = AttacheeRegistrationForm(request.POST, request.FILES)
        if form.is_valid():
            try:
                attachee = form.save(commit=False)
                attachee.application_number = f"APP-{uuid.uuid4().hex[:8].upper()}"
                attachee.application_date = date.today()
                attachee.status = 'pending'
                attachee.save()
                messages.success(request, 'Application submitted successfully!')
                return redirect('application_success', application_number=attachee.application_number)
            except Exception as e:
                messages.error(request, f'Error saving: {str(e)}')
        else:
            messages.error(request, 'Please correct errors below.')
    else:
        form = AttacheeRegistrationForm()
    return render(request, 'accounts/add_attachee.html', {'form': form})

def check_status(request):
    if request.method == 'POST':
        search = request.POST.get('search_query', '').strip()
        if search:
            attachee = Attachee.objects.filter(id_number=search).first()
            if not attachee:
                attachee = Attachee.objects.filter(phone=search).first()
            if not attachee:
                attachee = Attachee.objects.filter(email=search).first()
            if attachee:
                return render(request, 'accounts/check_status.html', {
                    'attachee': attachee,
                    'found': True,
                    'search_query': search
                })
            else:
                messages.error(request, f'No application found: {search}')
    return render(request, 'accounts/check_status.html', {'found': False})

def application_success(request, application_number):
    attachee = get_object_or_404(Attachee, application_number=application_number)
    return render(request, 'accounts/application_success.html', {'attachee': attachee})

def dashboard(request):
    total = Attachee.objects.count()
    pending = Attachee.objects.filter(status='pending').count()
    approved = Attachee.objects.filter(status='approved').count()
    recent = Attachee.objects.order_by('-application_date')[:10]
    return render(request, 'accounts/dashboard.html', {
        'total_applications': total,
        'pending_applications': pending,
        'approved_applications': approved,
        'recent_applications': recent,
    })
