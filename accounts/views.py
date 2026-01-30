from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import user_passes_test
from django.db.models import Q, Avg, Count
from django.http import FileResponse, HttpResponse
from django.utils import timezone
from django.core.mail import send_mail
from django.core.paginator import Paginator  
from django.conf import settings
from .models import Attachee, Evaluation, StudentFeedback
from .forms import AttacheeForm
import io, qrcode, textwrap, os, csv
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import inch
from reportlab.lib.utils import ImageReader

# Helper for Admin access
def is_admin(user):
    return user.is_superuser

def home(request):
    return render(request, 'accounts/home.html')

def add_attachee(request):
    if request.method == 'POST':
        form = AttacheeForm(request.POST, request.FILES)
        if form.is_valid():
            instance = form.save()
            return redirect('application_success', application_number=instance.tracking_id)
    else:
        form = AttacheeForm()
    return render(request, 'accounts/add_attachee.html', {'form': form})

def application_success(request, application_number):
    attachee = get_object_or_404(Attachee, tracking_id=application_number)
    return render(request, 'accounts/application_success.html', {'attachee': attachee})

def check_status(request):
    attachee = None
    if request.method == 'POST':
        query = request.POST.get('search_query')
        attachee = Attachee.objects.filter(
            Q(tracking_id=query) | Q(email=query) | Q(national_id_number=query)
        ).first()
        if attachee:
            today = timezone.now().date()
            attachee.is_expired = attachee.end_date < today
    return render(request, 'accounts/check_status.html', {'attachee': attachee})

@user_passes_test(is_admin)
def export_attachees(request):
    """Generates a CSV of the current filtered list"""
    status_filter = request.GET.get('status', '')
    search_query = request.GET.get('q', '')
    
    attachees = Attachee.objects.all()
    if search_query:
        attachees = attachees.filter(
            Q(first_name__icontains=search_query) | 
            Q(last_name__icontains=search_query) | 
            Q(tracking_id__icontains=search_query)
        )
    if status_filter:
        attachees = attachees.filter(status=status_filter)

    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="Eujim_Applicants_{timezone.now().date()}.csv"'
    
    writer = csv.writer(response)
    writer.writerow(['Tracking ID', 'First Name', 'Last Name', 'Email', 'Phone', 'Institution', 'Status', 'Applied On'])
    
    for a in attachees:
        writer.writerow([a.tracking_id, a.first_name, a.last_name, a.email, a.phone, a.institution, a.status, a.created_at])
    
    return response

@user_passes_test(is_admin)
def import_attachees(request):
    """Processes an uploaded CSV file to add records to the database"""
    if request.method == 'POST' and request.FILES.get('import_file'):
        csv_file = request.FILES['import_file']
        if not csv_file.name.endswith('.csv'):
            messages.error(request, 'Please upload a valid CSV file.')
            return redirect('dashboard')

        try:
            file_data = csv_file.read().decode("utf-8")
            lines = file_data.split("\n")
            
            for line in lines[1:]: # Skip header row
                fields = line.split(",")
                if len(fields) >= 6:
                    Attachee.objects.create(
                        first_name=fields[1].strip(),
                        last_name=fields[2].strip(),
                        email=fields[3].strip(),
                        phone=fields[4].strip(),
                        institution=fields[5].strip(),
                        status='Pending'
                    )
            messages.success(request, 'Data imported successfully.')
        except Exception as e:
            messages.error(request, f'Error processing file: {e}')
            
    return redirect('dashboard')

@user_passes_test(is_admin)
def dashboard(request):
    """Enhanced Dashboard handling Export, Clickable Stages, and Search"""
    
    # 1. CRITICAL: Handle Export before anything else
    if request.GET.get('export') == 'true':
        return export_attachees(request)

    search_query = request.GET.get('q', '')
    status_filter = request.GET.get('status', '')
    rows_per_page = request.GET.get('rows', 5)
    
    # 2. Base Queryset
    attachees_list = Attachee.objects.all().order_by('-created_at')
    
    # 3. Apply Search
    if search_query:
        attachees_list = attachees_list.filter(
            Q(first_name__icontains=search_query) | 
            Q(last_name__icontains=search_query) | 
            Q(tracking_id__icontains=search_query) | 
            Q(email__icontains=search_query)
        )

    # 4. Apply Stage Filter (Clickable Cards)
    if status_filter:
        attachees_list = attachees_list.filter(status=status_filter)

    # 5. Pagination
    paginator = Paginator(attachees_list, rows_per_page) 
    page_number = request.GET.get('page')
    attachees = paginator.get_page(page_number)

    return render(request, 'accounts/dashboard.html', {
        'attachees': attachees,
        'total': Attachee.objects.count(),
        'pending': Attachee.objects.filter(status='Pending').count(),
        'approved': Attachee.objects.filter(status='Approved').count(),
        'rejected': Attachee.objects.filter(status='Rejected').count(), 
        'completed': Attachee.objects.filter(status='Completed').count(),
        'query': search_query,
        'status_filter': status_filter,
        'rows': rows_per_page,
    })

@user_passes_test(is_admin)
def update_status(request, pk):
    if request.method == "POST":
        attachee = get_object_or_404(Attachee, pk=pk)
        new_status = request.POST.get('status')
        if new_status in dict(Attachee.STATUS_CHOICES):
            attachee.status = new_status
            if new_status == 'Completed':
                attachee.completion_date = timezone.now().date()
            attachee.save()
            
            subject = f'Application Status Update - Eujim Solutions'
            message = f"Hi {attachee.first_name}, your application ({attachee.tracking_id}) status has been updated to {new_status}."
            send_mail(subject, message, settings.EMAIL_HOST_USER, [attachee.email], fail_silently=True)
            
            messages.success(request, f"Status for {attachee.first_name} updated to {new_status}.")
    return redirect('dashboard')

@user_passes_test(is_admin)
def approve_student(request, attachee_id):
    attachee = get_object_or_404(Attachee, id=attachee_id)
    attachee.status = 'Approved'
    attachee.save()
    subject = 'Attachment Approved - Eujim Solutions'
    message = f"Hi {attachee.first_name}, your application (ID: {attachee.tracking_id}) is Approved. You can now download your Gate Pass from the portal."
    send_mail(subject, message, settings.EMAIL_HOST_USER, [attachee.email], fail_silently=True)
    messages.success(request, f"Application for {attachee.first_name} approved.")
    return redirect('dashboard')

@user_passes_test(is_admin)
def reject_student(request, attachee_id):
    attachee = get_object_or_404(Attachee, id=attachee_id)
    attachee.status = 'Rejected'
    attachee.save()
    subject = 'Application Update - Eujim Solutions'
    message = f"Hi {attachee.first_name}, unfortunately your application could not be approved at this time."
    send_mail(subject, message, settings.EMAIL_HOST_USER, [attachee.email], fail_silently=True)
    messages.error(request, f"Application for {attachee.first_name} has been rejected.")
    return redirect('dashboard')

@user_passes_test(is_admin)
def university_analytics(request):
    stats = Attachee.objects.values('institution').annotate(
        student_count=Count('id')
    ).order_by('-student_count')
    gender_stats = Attachee.objects.values('gender').annotate(count=Count('id'))
    return render(request, 'accounts/analytics.html', {
        'stats': stats,
        'gender_stats': gender_stats,
        'total_students': Attachee.objects.count()
    })

def submit_feedback(request, attachee_id):
    attachee = get_object_or_404(Attachee, id=attachee_id)
    if request.method == 'POST':
        StudentFeedback.objects.update_or_create(
            attachee=attachee,
            defaults={
                'mentorship_quality': request.POST.get('mentor'),
                'environment_rating': request.POST.get('env'),
                'resource_availability': request.POST.get('res'),
                'student_comments': request.POST.get('comments')
            }
        )
        return redirect('check_status')
    return render(request, 'accounts/submit_feedback.html', {'attachee': attachee})

# --- PDF BRANDING & UTILITY FUNCTIONS ---

def draw_header_and_border(p):
    brand_color = (85/255, 212/255, 122/255) 
    p.setStrokeColorRGB(*brand_color)
    p.setLineWidth(3); p.rect(0.4*inch, 0.4*inch, 7.5*inch, 10.9*inch)
    p.setLineWidth(1); p.rect(0.45*inch, 0.45*inch, 7.4*inch, 10.8*inch)
    logo_path = os.path.join(settings.BASE_DIR, 'static/images/logo.png')
    if os.path.exists(logo_path):
        p.drawImage(logo_path, 3.65*inch, 10.4*inch, width=1.0*inch, preserveAspectRatio=True, mask='auto')
    p.setFillColorRGB(0.1, 0.1, 0.1); p.setFont("Helvetica-Bold", 14)
    p.drawCentredString(4.15*inch, 10.2*inch, "EUJIM SOLUTIONS LIMITED")
    p.setFont("Helvetica", 9); p.drawCentredString(4.15*inch, 10.05*inch, "Gesora Road, Utawala")
    p.drawCentredString(4.15*inch, 9.9*inch, "Tel: +254 113281424 / +254 718099959")
    p.drawCentredString(4.15*inch, 9.75*inch, "Email: info@eujimsolutions.com | Web: www.eujimsolutions.com")
    p.setStrokeColorRGB(*brand_color); p.line(0.8*inch, 9.6*inch, 7.5*inch, 9.6*inch)
    p.setFillColorRGB(0, 0, 0)

def draw_footer(p, attachee, current_y):
    footer_y = current_y 
    sig_path = os.path.join(settings.BASE_DIR, 'static/images/signature.png')
    if os.path.exists(sig_path):
        p.drawImage(sig_path, 0.8*inch, footer_y + 0.1*inch, width=1.4*inch, preserveAspectRatio=True, mask='auto')
    p.setFont("Helvetica-Bold", 10); p.drawString(0.8*inch, footer_y, "__________________________")
    p.drawString(0.8*inch, footer_y - 0.15*inch, "Ombwayo Michael")
    p.setFont("Helvetica", 9); p.drawString(0.8*inch, footer_y - 0.3*inch, "CEO and Founder")
    p.drawString(0.8*inch, footer_y - 0.45*inch, "Eujim Solutions Limited")
    
    p.setStrokeColorRGB(0.6, 0.1, 0.1); p.setLineWidth(1.2)
    p.circle(4.15*inch, footer_y - 0.1*inch, 38, stroke=1, fill=0)
    p.setFont("Helvetica-Bold", 7); p.setFillColorRGB(0.6, 0.1, 0.1)
    p.drawCentredString(4.15*inch, footer_y + 0.15*inch, "OFFICIAL SEAL")
    p.drawCentredString(4.15*inch, footer_y - 0.05*inch, "EUJIM SOLUTIONS")
    p.drawCentredString(4.15*inch, footer_y - 0.25*inch, "VERIFIED")
    p.setStrokeColorRGB(0, 0, 0); p.setFillColorRGB(0, 0, 0)
    
    qr = qrcode.make(f"VERIFIED: {attachee.tracking_id}"); qb = io.BytesIO()
    qr.save(qb, format='PNG'); qb.seek(0)
    p.drawImage(ImageReader(qb), 6.5*inch, footer_y - 0.5*inch, width=0.85*inch, height=0.85*inch)

def download_completion_letter(request, attachee_id):
    attachee = get_object_or_404(Attachee, id=attachee_id)
    duration_weeks = (attachee.end_date - attachee.start_date).days // 7
    
    buffer = io.BytesIO(); p = canvas.Canvas(buffer, pagesize=A4); draw_header_and_border(p)
    p.setFont("Helvetica-Bold", 13); p.drawCentredString(4.15*inch, 9.3*inch, "CERTIFICATE OF COMPLETION")
    
    p.setFont("Helvetica", 11)
    paras = [
        f"This letter serves to formally certify that you, {attachee.first_name} {attachee.last_name}, a student from {attachee.institution}, have successfully completed your comprehensive industrial attachment at EUJIM SOLUTIONS LIMITED. The program ran from {attachee.start_date.strftime('%d %B %Y')} to {attachee.end_date.strftime('%d %B %Y')}, totaling {duration_weeks} weeks of professional engagement under Tracking ID: {attachee.tracking_id}.",
        f"During this tenure, you were fully integrated into our technical operations. You demonstrated an exceptional work ethic, showing great initiative in problem-solving and technical execution. You were involved in numerous projects where you consistently met project deadlines and maintained high-quality standards.",
        f"In addition to your technical growth, you exhibited strong interpersonal skills and professional discipline. This certificate recognizes your successful completion of all attachment requirements. We highly appreciate your contribution to our team and wish you the very best in your future career pursuits."
    ]
    
    y = 8.9*inch
    for txt in paras:
        to = p.beginText(0.8*inch, y); to.setLeading(16)
        wrapped = textwrap.wrap(txt, width=90)
        for line in wrapped: to.textLine(line)
        p.drawText(to); y -= (len(wrapped) * 16) + 18
    
    draw_footer(p, attachee, max(y - 0.5*inch, 1.8*inch))
    p.showPage(); p.save(); buffer.seek(0)
    return FileResponse(buffer, as_attachment=False, content_type='application/pdf', filename=f'Completion_{attachee.tracking_id}.pdf')

def download_recommendation_letter(request, attachee_id):
    attachee = get_object_or_404(Attachee, id=attachee_id)
    duration_weeks = (attachee.end_date - attachee.start_date).days // 7
    
    buffer = io.BytesIO(); p = canvas.Canvas(buffer, pagesize=A4); draw_header_and_border(p)
    p.setFont("Helvetica-Bold", 13); p.drawCentredString(4.15*inch, 9.3*inch, "LETTER OF RECOMMENDATION")
    
    p.setFont("Helvetica", 11)
    paras = [
        f"It is with great pleasure that I recommend you, {attachee.first_name} {attachee.last_name}, for future professional roles or academic pursuits. You recently completed a rigorous {duration_weeks}-week industrial attachment at EUJIM SOLUTIONS (ID: {attachee.tracking_id}) where you made a lasting impression on our team.",
        f"Throughout your time with us, you displayed a commendable work ethic and a proactive mindset. You proved to be a reliable, disciplined, and technically competent individual who consistently exceeded our expectations in every task assigned.",
        f"Beyond technical tasks, you were a collaborative team player who interacted positively with colleagues and demonstrated a high level of professional integrity. We are confident you possess the character to be a valuable asset to any organization, and we wish you continued success."
    ]
    
    y = 8.9*inch
    for txt in paras:
        to = p.beginText(0.8*inch, y); to.setLeading(16)
        wrapped = textwrap.wrap(txt, width=90)
        for line in wrapped: to.textLine(line)
        p.drawText(to); y -= (len(wrapped) * 16) + 18
    
    draw_footer(p, attachee, max(y - 0.5*inch, 1.8*inch))
    p.showPage(); p.save(); buffer.seek(0)
    return FileResponse(buffer, as_attachment=False, content_type='application/pdf', filename=f'Recommendation_{attachee.tracking_id}.pdf')

def download_gate_pass(request, attachee_id):
    attachee = get_object_or_404(Attachee, id=attachee_id)
    if attachee.status != 'Approved':
        return HttpResponse("Unauthorized: Gate Pass is only available for active, approved attachments.", status=403)

    buffer = io.BytesIO(); p = canvas.Canvas(buffer, pagesize=A4); draw_header_and_border(p)
    p.setFont("Helvetica-Bold", 14); p.drawCentredString(4.15*inch, 9.3*inch, "OFFICIAL GATE PASS & ADMISSION LETTER")
    p.setFont("Helvetica-Bold", 11); p.drawString(1.0*inch, 8.8*inch, "APPLICANT DETAILS")
    p.line(1.0*inch, 8.75*inch, 3.0*inch, 8.75*inch)
    
    p.setFont("Helvetica", 10)
    details = [
        f"Full Name: {attachee.first_name} {attachee.last_name}",
        f"Phone Number: {attachee.phone}",
        f"National ID: {attachee.national_id_number}",
        f"Gender: {attachee.gender}",
        f"Institution: {attachee.institution}",
        f"Tracking ID: {attachee.tracking_id}",
        f"Duration: {attachee.start_date.strftime('%d %b %Y')} to {attachee.end_date.strftime('%d %b %Y')}"
    ]
    
    y_detail = 8.5*inch
    for item in details:
        p.drawString(1.0*inch, y_detail, item)
        y_detail -= 0.22*inch

    p.setFont("Helvetica-Bold", 11); p.drawString(1.0*inch, y_detail - 0.2*inch, "TERMS OF ENGAGEMENT")
    p.line(1.0*inch, y_detail - 0.25*inch, 3.2*inch, y_detail - 0.25*inch)
    
    p.setFont("Helvetica", 11)
    welcome_text = (
        f"We are pleased to welcome you, {attachee.first_name}, to EUJIM SOLUTIONS LIMITED. "
        f"During the stated period, you will be an integral part of our team. "
        f"Please note that you are required to report to the office from Monday to Friday, "
        f"between 9:00 AM and 4:00 PM."
    )
    
    y_para = y_detail - 0.5*inch
    to = p.beginText(1.0*inch, y_para); to.setLeading(16)
    wrapped = textwrap.wrap(welcome_text, width=85)
    for line in wrapped: to.textLine(line)
    p.drawText(to)
    
    current_y = y_para - (len(wrapped) * 16) - 0.3*inch
    draw_footer(p, attachee, max(current_y, 1.8*inch))
    
    p.showPage(); p.save(); buffer.seek(0)
    return FileResponse(buffer, as_attachment=False, content_type='application/pdf', filename=f'GatePass_{attachee.tracking_id}.pdf')