from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import user_passes_test
from django.db.models import Q, Avg, Count
from django.http import FileResponse, HttpResponse
from django.utils import timezone
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags
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
            
            # --- Application Received Email ---
            action_url = request.build_absolute_uri('/check-status/')
            body_text = (
                f"Your application has been well received and is currently in progress. "
                f"Please note that your tracking number will be used as your Reference Number "
                f"to track progress and verify the authenticity of your documents."
            )
            
            html_content = render_to_string('accounts/email_template.html', {
                'name': instance.first_name,
                'body_text': body_text,
                'tracking_number': instance.tracking_id,
                'action_url': action_url,
                'action_text': 'Track Application',
                'footer_note': "In case you need assistance, contact us at info@eujimsolutions.com or +254 718099959."
            })
            
            email = EmailMultiAlternatives(
                subject=f"Application Received - Ref: {instance.tracking_id}",
                body=strip_tags(html_content),
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=[instance.email]
            )
            email.attach_alternative(html_content, "text/html")
            email.send(fail_silently=True)

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
    writer.writerow(['Reference No.', 'First Name', 'Last Name', 'Email', 'Phone', 'Institution', 'Status', 'Applied On'])
    
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
            
            for line in lines[1:]: 
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
    if request.GET.get('export') == 'true':
        return export_attachees(request)

    search_query = request.GET.get('q', '')
    status_filter = request.GET.get('status', '')
    rows_per_page = request.GET.get('rows', 5)
    
    attachees_list = Attachee.objects.all().order_by('-created_at')
    
    if search_query:
        attachees_list = attachees_list.filter(
            Q(first_name__icontains=search_query) | 
            Q(last_name__icontains=search_query) | 
            Q(tracking_id__icontains=search_query) | 
            Q(email__icontains=search_query)
        )

    if status_filter:
        attachees_list = attachees_list.filter(status=status_filter)

    paginator = Paginator(attachees_list, rows_per_page) 
    page_number = request.GET.get('page')
    attachees = paginator.get_page(page_number)

    return render(request, 'accounts/dashboard.html', {
        'attachees': attachees,
        'total': Attachee.objects.count(),
        'pending': Attachee.objects.filter(status='Pending').count(),
        'approved': Attachee.objects.filter(status='Approved').count(),
        'in_progress': Attachee.objects.filter(status='In-Progress').count(),
        'rejected': Attachee.objects.filter(status='Rejected').count(), 
        'completed': Attachee.objects.filter(status='Completed').count(),
        'query': search_query,
        'status_filter': status_filter,
        'rows': rows_per_page,
    })

@user_passes_test(is_admin)
def update_status(request, pk):
    """Detailed Email Messaging for Approvals, Admittance, and Completions"""
    if request.method == "POST":
        attachee = get_object_or_404(Attachee, pk=pk)
        old_status = attachee.status
        new_status = request.POST.get('status')
        new_notes = request.POST.get('admin_notes')

        if new_status in dict(Attachee.STATUS_CHOICES):
            attachee.status = new_status
            attachee.admin_notes = new_notes 
            
            if new_status == 'Completed':
                attachee.completion_date = timezone.now().date()
            attachee.save()
            
            if old_status != new_status:
                action_url = request.build_absolute_uri('/check-status/')
                
                status_map = {
                    'Approved': (
                        "Congratulations! Your application has been APPROVED. We expect total discipline and full cooperation during your tenure with us.", 
                        "Get Gate Pass"
                    ),
                    'In-Progress': (
                        f"We are pleased to inform you that you have officially started your attachment. "
                        f"Your tenure is scheduled from {attachee.start_date.strftime('%d %b %Y')} to {attachee.end_date.strftime('%d %b %Y')}. "
                        "You can now download your official Attachment ID card.", 
                        "Download ID Card"
                    ),
                    'Rejected': (
                        "We regret to inform you that your application was not successful at this time.", 
                        "Check Status"
                    ),
                    'Completed': (
                        "Your attachment period is now COMPLETED. We truly appreciate the time you spent with us and wish you the very best in your future endeavors.", 
                        "Get Documents"
                    )
                }
                
                if new_status in status_map:
                    body_text, btn_label = status_map[new_status]
                    html_content = render_to_string('accounts/email_template.html', {
                        'name': attachee.first_name,
                        'body_text': body_text,
                        'tracking_number': attachee.tracking_id,
                        'action_url': action_url,
                        'action_text': btn_label,
                        'footer_note': "For any assistance, contact info@eujimsolutions.com"
                    })
                    
                    email = EmailMultiAlternatives(
                        subject=f"Status Update - Ref: {attachee.tracking_id}",
                        body=strip_tags(html_content),
                        from_email=settings.DEFAULT_FROM_EMAIL,
                        to=[attachee.email]
                    )
                    email.attach_alternative(html_content, "text/html")
                    email.send(fail_silently=True)
            
            messages.success(request, f"Status for {attachee.first_name} updated to {new_status}.")
    return redirect('dashboard')

# --- PDF BRANDING & UTILITY FUNCTIONS ---

def draw_header_and_border(p):
    """Sharp letterhead placement with double-line brand borders"""
    brand_color = (85/255, 212/255, 122/255) 
    p.setStrokeColorRGB(*brand_color)
    p.setLineWidth(3); p.rect(0.4*inch, 0.4*inch, 7.5*inch, 10.9*inch)
    p.setLineWidth(1); p.rect(0.45*inch, 0.45*inch, 7.4*inch, 10.8*inch)
    p.setFillColorRGB(0, 0, 0) 

    letterhead_path = os.path.join(settings.BASE_DIR, 'static/images/letterhead.png')
    
    if os.path.exists(letterhead_path):
        banner_height = 1.3 * inch
        p.drawImage(letterhead_path, 0.5*inch, A4[1] - banner_height - 0.5*inch, width=7.27*inch, height=banner_height, mask='auto', preserveAspectRatio=True)
    else:
        p.setFillColorRGB(0.1, 0.1, 0.1); p.setFont("Helvetica-Bold", 14)
        p.drawCentredString(4.15*inch, 10.2*inch, "EUJIM SOLUTIONS LIMITED")
        p.setFont("Helvetica", 9); p.drawCentredString(4.15*inch, 10.05*inch, "Gesora Road, Utawala")
        p.setFillColorRGB(0, 0, 0)

def draw_footer(p, attachee, current_y):
    footer_y = max(current_y, 1.8*inch)
    
    sig_path = os.path.join(settings.BASE_DIR, 'static/images/signature.png')
    if os.path.exists(sig_path):
        p.drawImage(sig_path, 3.7*inch, footer_y + 0.15*inch, width=1.3*inch, preserveAspectRatio=True, mask='auto')
    
    p.setFont("Helvetica-Bold", 9)
    p.drawCentredString(4.4*inch, footer_y + 0.12*inch, "__________________________")
    p.drawCentredString(4.4*inch, footer_y - 0.02*inch, "Ombwayo Michael")
    p.setFont("Helvetica", 8)
    p.drawCentredString(4.4*inch, footer_y - 0.12*inch, "CEO and Founder, Eujim Solutions Ltd")
    
    stamp_x = 3.2*inch
    stamp_y = footer_y - 1.3*inch
    stamp_width = 2.4*inch
    stamp_height = 1.1*inch
    
    p.setStrokeColorRGB(0.2, 0.4, 0.7); p.setLineWidth(1.5)
    p.rect(stamp_x, stamp_y, stamp_width, stamp_height, stroke=1, fill=0)
    p.setFillColorRGB(0.2, 0.4, 0.7); p.setFont("Helvetica-Bold", 8.5)
    p.drawCentredString(stamp_x + (stamp_width/2), stamp_y + 0.90*inch, "EUJIM SOLUTIONS LIMITED")
    
    p.setFont("Helvetica-Bold", 7.5)
    p.drawCentredString(stamp_x + (stamp_width/2), stamp_y + 0.75*inch, "P.O. BOX 7034-00220, NAIROBI")
    
    p.setFillColorRGB(0.8, 0.1, 0.1); p.setFont("Helvetica-Bold", 10)
    date_text = attachee.completion_date.strftime('%d %b %Y').upper() if attachee.completion_date else timezone.now().strftime('%d %b %Y').upper()
    p.drawCentredString(stamp_x + (stamp_width/2), stamp_y + 0.45*inch, date_text)
    
    p.setFillColorRGB(0.2, 0.4, 0.7); p.setFont("Helvetica-Bold", 6.5)
    p.drawCentredString(stamp_x + (stamp_width/2), stamp_y + 0.22*inch, "Email: info@eujimsolutions.com")
    p.drawCentredString(stamp_x + (stamp_width/2), stamp_y + 0.08*inch, "Tel: +254 113281424 / +254 718099959")

    qr = qrcode.make(f"VERIFIED REF: {attachee.tracking_id}"); qb = io.BytesIO()
    qr.save(qb, format='PNG'); qb.seek(0)
    p.drawImage(ImageReader(qb), 6.0*inch, stamp_y, width=1.0*inch, height=1.0*inch)

def download_completion_letter(request, attachee_id):
    attachee = get_object_or_404(Attachee, id=attachee_id)
    is_male = attachee.gender.lower() == 'male'
    subj, poss, obj = ("He", "his", "him") if is_male else ("She", "her", "her")
    duration_weeks = (attachee.end_date - attachee.start_date).days // 7
    
    buffer = io.BytesIO(); p = canvas.Canvas(buffer, pagesize=A4); draw_header_and_border(p)
    y_title = 9.2*inch 
    y_start = 8.9*inch
    p.setFont("Helvetica-Bold", 13)
    p.drawCentredString(4.15*inch, y_title, f"CERTIFICATE OF COMPLETION ({attachee.tracking_id})")
    
    p.setFont("Helvetica", 11)
    paras = [
        f"This letter serves to formally certify that {attachee.first_name} {attachee.last_name}, a student from {attachee.institution}, has successfully completed {poss} comprehensive industrial attachment at EUJIM SOLUTIONS LIMITED. The program ran from {attachee.start_date.strftime('%d %B %Y')} to {attachee.end_date.strftime('%d %B %Y')}, totaling {duration_weeks} weeks of professional engagement under Reference No: {attachee.tracking_id}.",
        f"During this tenure, {subj.lower()} was fully integrated into our technical operations. {subj} demonstrated an exceptional work ethic, showing great initiative in problem-solving and technical execution. {subj} was involved in numerous projects where {subj.lower()} consistently met project deadlines and maintained high-quality standards.",
        f"In addition to {poss} technical growth, {subj.lower()} exhibited strong interpersonal skills and professional discipline. This certificate recognizes {poss} successful completion of all attachment requirements. We highly appreciate {poss} contribution to our team and wish {obj} the very best in {poss} future career pursuits."
    ]
    
    y = y_start
    for txt in paras:
        to = p.beginText(0.8*inch, y); to.setLeading(14)
        wrapped = textwrap.wrap(txt, width=90)
        for line in wrapped: to.textLine(line)
        p.drawText(to); y -= (len(wrapped) * 14) + 10
    
    draw_footer(p, attachee, y - 0.2*inch)
    p.showPage(); p.save(); buffer.seek(0)
    return FileResponse(buffer, as_attachment=False, content_type='application/pdf', filename=f'Completion_{attachee.tracking_id}.pdf')

def download_recommendation_letter(request, attachee_id):
    attachee = get_object_or_404(Attachee, id=attachee_id)
    is_male = attachee.gender.lower() == 'male'
    subj, poss, obj = ("He", "his", "him") if is_male else ("She", "her", "her")
    duration_weeks = (attachee.end_date - attachee.start_date).days // 7
    
    buffer = io.BytesIO(); p = canvas.Canvas(buffer, pagesize=A4); draw_header_and_border(p)
    y_title = 9.2*inch
    y_start = 8.9*inch
    p.setFont("Helvetica-Bold", 13)
    p.drawCentredString(4.15*inch, y_title, f"LETTER OF RECOMMENDATION ({attachee.tracking_id})")
    
    p.setFont("Helvetica", 11)
    paras = [
        f"It is with great pleasure that I recommend {attachee.first_name} {attachee.last_name} for future professional roles or academic pursuits. {subj} recently completed a rigorous {duration_weeks}-week industrial attachment at EUJIM SOLUTIONS where {subj.lower()} made a lasting impression on our team under Reference No: {attachee.tracking_id}.",
        f"Throughout {poss} time with us, {subj.lower()} displayed a commendable work ethic and a proactive mindset. {subj} proved to be a reliable, disciplined, and technically competent individual who consistently exceeded our expectations in every task assigned.",
        f"Beyond technical tasks, {subj.lower()} was a collaborative team player who interacted positively with colleagues and demonstrated a high level of professional integrity. We are confident {subj.lower()} possesses the character to be a valuable asset to any organization, and we wish {obj} continued success."
    ]
    
    y = y_start
    for txt in paras:
        to = p.beginText(0.8*inch, y); to.setLeading(14)
        wrapped = textwrap.wrap(txt, width=90)
        for line in wrapped: to.textLine(line)
        p.drawText(to); y -= (len(wrapped) * 14) + 10
    
    draw_footer(p, attachee, y - 0.2*inch)
    p.showPage(); p.save(); buffer.seek(0)
    return FileResponse(buffer, as_attachment=False, content_type='application/pdf', filename=f'Recommendation_{attachee.tracking_id}.pdf')

def download_gate_pass(request, attachee_id):
    attachee = get_object_or_404(Attachee, id=attachee_id)
    buffer = io.BytesIO(); p = canvas.Canvas(buffer, pagesize=A4); draw_header_and_border(p)
    y_title = 9.2*inch
    y_detail = 8.8*inch
    p.setFont("Helvetica-Bold", 14)
    p.drawCentredString(4.15*inch, y_title, f"OFFICIAL GATE PASS & ADMISSION LETTER ({attachee.tracking_id})")
    p.setFont("Helvetica-Bold", 11); p.drawString(1.0*inch, y_detail + 0.1*inch, "APPLICANT DETAILS")
    p.line(1.0*inch, y_detail + 0.05*inch, 3.0*inch, y_detail + 0.05*inch)
    p.setFont("Helvetica", 10)
    details = [
        f"Full Name: {attachee.first_name} {attachee.last_name}",
        f"Phone Number: {attachee.phone}",
        f"National ID: {attachee.national_id_number}",
        f"Gender: {attachee.gender}",
        f"Institution: {attachee.institution}",
        f"Reference No: {attachee.tracking_id}",
        f"Duration: {attachee.start_date.strftime('%d %b %Y')} to {attachee.end_date.strftime('%d %b %Y')}"
    ]
    curr_y = y_detail - 0.1*inch
    for item in details:
        p.drawString(1.0*inch, curr_y, item); curr_y -= 0.16*inch
    p.setFont("Helvetica-Bold", 11); p.drawString(1.0*inch, curr_y - 0.05*inch, "TERMS OF ENGAGEMENT")
    p.line(1.0*inch, curr_y - 0.1*inch, 3.2*inch, curr_y - 0.1*inch)
    welcome_text = (
        f"We are pleased to welcome you, {attachee.first_name}, to EUJIM SOLUTIONS LIMITED. "
        "During the stated period, you will be an integral part of our team. "
        "Please note that you are required to report to the office from Monday to Friday, "
        "between 9:00 AM and 4:00 PM."
    )
    p.setFont("Helvetica", 10)
    to = p.beginText(1.0*inch, curr_y - 0.25*inch); to.setLeading(14)
    wrapped = textwrap.wrap(welcome_text, width=95)
    for line in wrapped: to.textLine(line)
    p.drawText(to)
    draw_footer(p, attachee, curr_y - 1.2*inch)
    p.showPage(); p.save(); buffer.seek(0)
    return FileResponse(buffer, as_attachment=False, content_type='application/pdf', filename=f'GatePass_{attachee.tracking_id}.pdf')

# --- UPDATED: ID CARD WITH CONTACT DETAILS ---
def download_id_card(request, attachee_id):
    attachee = get_object_or_404(Attachee, id=attachee_id)
    buffer = io.BytesIO()
    id_size = (3.375 * inch, 2.125 * inch)
    p = canvas.Canvas(buffer, pagesize=id_size)
    brand_color = (85/255, 212/255, 122/255)
    p.setFillColorRGB(*brand_color)
    p.rect(0, 1.6*inch, 3.375*inch, 0.525*inch, fill=1)
    p.setFillColorRGB(1, 1, 1)
    p.setFont("Helvetica-Bold", 10)
    p.drawCentredString(1.68*inch, 1.8*inch, "EUJIM SOLUTIONS LTD")
    p.setFillColorRGB(0, 0, 0)
    p.setFont("Helvetica-Bold", 9)
    p.drawCentredString(1.68*inch, 1.4*inch, f"{attachee.first_name} {attachee.last_name}")
    p.setFont("Helvetica", 7)
    
    # ADDED ID, PHONE, AND EMAIL AS REQUESTED
    p.drawString(0.2*inch, 1.15*inch, f"ID NO: {attachee.national_id_number}")
    p.drawString(0.2*inch, 1.0*inch, f"PHONE: {attachee.phone}")
    p.drawString(0.2*inch, 0.85*inch, f"EMAIL: {attachee.email}")
    p.drawString(0.2*inch, 0.7*inch, f"REF NO: {attachee.tracking_id}")
    p.drawString(0.2*inch, 0.55*inch, f"INST: {attachee.institution}")
    
    p.setFillColorRGB(0.8, 0.1, 0.1)
    p.setFont("Helvetica-Bold", 6.5)
    valid_text = f"VALID: {attachee.start_date.strftime('%b %Y')} - {attachee.end_date.strftime('%b %Y')}"
    p.drawCentredString(1.68*inch, 0.3*inch, valid_text)
    
    qr_data = f"REF:{attachee.tracking_id} | {attachee.first_name}"
    qr = qrcode.make(qr_data); qb = io.BytesIO()
    qr.save(qb, format='PNG'); qb.seek(0)
    p.drawImage(ImageReader(qb), 2.5*inch, 0.5*inch, width=0.7*inch, height=0.7*inch)
    p.showPage(); p.save(); buffer.seek(0)
    return FileResponse(buffer, as_attachment=False, content_type='application/pdf', filename=f'ID_{attachee.tracking_id}.pdf')

@user_passes_test(is_admin)
def approve_student(request, attachee_id):
    attachee = get_object_or_404(Attachee, id=attachee_id)
    attachee.status = 'Approved'; attachee.save()
    messages.success(request, f"Application for {attachee.first_name} approved.")
    return redirect('dashboard')

@user_passes_test(is_admin)
def reject_student(request, attachee_id):
    attachee = get_object_or_404(Attachee, id=attachee_id)
    attachee.status = 'Rejected'; attachee.save()
    messages.error(request, f"Application for {attachee.first_name} rejected.")
    return redirect('dashboard')

@user_passes_test(is_admin)
def university_analytics(request):
    stats = Attachee.objects.values('institution').annotate(student_count=Count('id')).order_by('-student_count')
    gender_stats = Attachee.objects.values('gender').annotate(count=Count('id'))
    return render(request, 'accounts/analytics.html', {'stats': stats, 'gender_stats': gender_stats, 'total_students': Attachee.objects.count()})

def submit_feedback(request, attachee_id):
    attachee = get_object_or_404(Attachee, id=attachee_id)
    if request.method == 'POST':
        StudentFeedback.objects.update_or_create(attachee=attachee, defaults={'mentorship_quality': request.POST.get('mentor'), 'environment_rating': request.POST.get('env'), 'resource_availability': request.POST.get('res'), 'student_comments': request.POST.get('comments')})
        return redirect('check_status')
    return render(request, 'accounts/submit_feedback.html', {'attachee': attachee})