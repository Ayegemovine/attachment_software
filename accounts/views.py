from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import user_passes_test
from django.db.models import Q, Count
from django.http import FileResponse, HttpResponse
from django.utils import timezone
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.core.paginator import Paginator
from django.conf import settings
from .models import Attachee, StudentFeedback
from .forms import AttacheeForm
import io
import qrcode
import textwrap
import os
import csv
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
                "Your application has been well received and is currently in "
                "progress. Please note that your tracking number will be used "
                "as your Reference Number to track progress and verify the "
                "authenticity of your documents."
            )

            html_content = render_to_string('accounts/email_template.html', {
                'name': instance.first_name,
                'body_text': body_text,
                'tracking_number': instance.tracking_id,
                'action_url': action_url,
                'action_text': 'Track Application',
                'footer_note': (
                    "In case you need assistance, contact us at "
                    "info@eujimsolutions.com or +254 718099959."
                )
            })

            email = EmailMultiAlternatives(
                subject=f"Application Received - Ref: {instance.tracking_id}",
                body=strip_tags(html_content),
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=[instance.email]
            )
            email.attach_alternative(html_content, "text/html")
            email.send(fail_silently=True)

            return redirect(
                'application_success',
                application_number=instance.tracking_id
            )
    else:
        form = AttacheeForm()
    return render(request, 'accounts/add_attachee.html', {'form': form})


def application_success(request, application_number):
    attachee = get_object_or_404(Attachee, tracking_id=application_number)
    return render(
        request,
        'accounts/application_success.html',
        {'attachee': attachee}
    )


def check_status(request):
    attachee = None
    if request.method == 'POST':
        query = request.POST.get('search_query')
        attachee = Attachee.objects.filter(
            Q(tracking_id=query) |
            Q(email=query) |
            Q(national_id_number=query)
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
    dt_str = timezone.now().date()
    response['Content-Disposition'] = f'attachment; filename="Exp_{dt_str}.csv"'

    writer = csv.writer(response)
    writer.writerow([
        'Reference No.', 'First Name', 'Last Name', 'Email',
        'Phone', 'Institution', 'Status', 'Applied On'
    ])

    for a in attachees:
        writer.writerow([
            a.tracking_id, a.first_name, a.last_name, a.email,
            a.phone, a.institution, a.status, a.created_at
        ])

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
    """Detailed Email Messaging for Approvals and admittance"""
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
                        "Congratulations! Your application has been APPROVED. "
                        "We expect total discipline during your tenure.",
                        "Get Gate Pass"
                    ),
                    'In-Progress': (
                        f"You have started your attachment. Your tenure is "
                        f"from {attachee.start_date.strftime('%d %b %Y')} to "
                        f"{attachee.end_date.strftime('%d %b %Y')}. You can "
                        "now download your official Attachment ID card.",
                        "Download ID Card"
                    ),
                    'Rejected': (
                        "We regret to inform you that your application was "
                        "not successful at this time.",
                        "Check Status"
                    ),
                    'Completed': (
                        "Your attachment period is now COMPLETED. We wish you "
                        "the very best in your future endeavors.",
                        "Get Documents"
                    )
                }

                if new_status in status_map:
                    body_text, btn_label = status_map[new_status]
                    html_content = render_to_string(
                        'accounts/email_template.html', {
                            'name': attachee.first_name,
                            'body_text': body_text,
                            'tracking_number': attachee.tracking_id,
                            'action_url': action_url,
                            'action_text': btn_label,
                            'footer_note': "Contact info@eujimsolutions.com"
                        }
                    )

                    email = EmailMultiAlternatives(
                        subject=f"Update - Ref: {attachee.tracking_id}",
                        body=strip_tags(html_content),
                        from_email=settings.DEFAULT_FROM_EMAIL,
                        to=[attachee.email]
                    )
                    email.attach_alternative(html_content, "text/html")
                    email.send(fail_silently=True)

            messages.success(
                request,
                f"Status for {attachee.first_name} updated to {new_status}."
            )
    return redirect('dashboard')


# --- PDF BRANDING & UTILITY FUNCTIONS ---

def draw_header_and_border(p):
    """Sharp letterhead placement with double-line brand borders"""
    brand_color = (85/255, 212/255, 122/255)
    p.setStrokeColorRGB(*brand_color)
    p.setLineWidth(3)
    p.rect(0.4*inch, 0.4*inch, 7.5*inch, 10.9*inch)
    p.setLineWidth(1)
    p.rect(0.45*inch, 0.45*inch, 7.4*inch, 10.8*inch)
    p.setFillColorRGB(0, 0, 0)

    l_path = os.path.join(settings.BASE_DIR, 'static/images/letterhead.png')

    if os.path.exists(l_path):
        bh = 1.3 * inch
        p.drawImage(
            l_path, 0.5*inch, A4[1] - bh - 0.5*inch, width=7.27*inch,
            height=bh, mask='auto', preserveAspectRatio=True
        )
    else:
        p.setFillColorRGB(0.1, 0.1, 0.1)
        p.setFont("Helvetica-Bold", 14)
        p.drawCentredString(4.15*inch, 10.2*inch, "EUJIM SOLUTIONS LIMITED")
        p.setFont("Helvetica", 9)
        p.drawCentredString(4.15*inch, 10.05*inch, "Gesora Road, Utawala")
        p.setFillColorRGB(0, 0, 0)


def draw_footer(p, attachee, current_y):
    footer_y = max(current_y, 1.8*inch)
    s_path = os.path.join(settings.BASE_DIR, 'static/images/signature.png')
    if os.path.exists(s_path):
        p.drawImage(
            s_path, 3.7*inch, footer_y + 0.15*inch, width=1.3*inch,
            preserveAspectRatio=True, mask='auto'
        )

    p.setFont("Helvetica-Bold", 9)
    p.drawCentredString(4.4*inch, footer_y + 0.12*inch, "___________________")
    p.drawCentredString(4.4*inch, footer_y - 0.02*inch, "Ombwayo Michael")
    p.setFont("Helvetica", 8)
    p.drawCentredString(4.4*inch, footer_y - 0.12*inch, "CEO, Eujim Solutions")

    # --- Compact Official Company Stamp ---
    stamp_x, stamp_y = 3.5*inch, footer_y - 1.4*inch
    s_w, s_h = 2.2*inch, 1.2*inch 

    p.setStrokeColorRGB(0.2, 0.4, 0.7)
    p.setLineWidth(1.5)
    p.rect(stamp_x, stamp_y, s_w, s_h, stroke=1, fill=0)
    
    p.setFillColorRGB(0.2, 0.4, 0.7)
    p.setFont("Helvetica-Bold", 8.5)
    p.drawCentredString(stamp_x + 1.1*inch, stamp_y + 1.0*inch, "EUJIM SOLUTIONS LIMITED")

    p.setFont("Helvetica-Bold", 7.5)
    p.drawCentredString(stamp_x + 1.1*inch, stamp_y + 0.85*inch, "P.O. BOX 7034-00200 NAIROBI")

    p.setFillColorRGB(0.8, 0.1, 0.1)
    p.setFont("Helvetica-Bold", 10)
    dt_txt = (
        attachee.completion_date.strftime('%d %b %Y').upper()
        if attachee.completion_date
        else timezone.now().strftime('%d %b %Y').upper()
    )
    p.drawCentredString(stamp_x + 1.1*inch, stamp_y + 0.55*inch, dt_txt)

    p.setFillColorRGB(0.2, 0.4, 0.7)
    p.setFont("Helvetica-Bold", 7.2) 
    p.drawCentredString(stamp_x + 1.1*inch, stamp_y + 0.33*inch, "Email: info@eujimsolutions.com")
    p.drawCentredString(stamp_x + 1.1*inch, stamp_y + 0.15*inch, "TEL: 0113281424/0718099959")

    qr = qrcode.make(f"VERIFIED REF: {attachee.tracking_id}")
    qb = io.BytesIO()
    qr.save(qb, format='PNG')
    qb.seek(0)
    p.drawImage(ImageReader(qb), 6.1*inch, stamp_y, width=inch, height=inch)


def download_completion_letter(request, attachee_id):
    attachee = get_object_or_404(Attachee, id=attachee_id)

    is_male = attachee.gender.lower() == 'male'
    subj = "He" if is_male else "She"
    poss = "his" if is_male else "her"
    obj = "him" if is_male else "her"

    duration_days = (attachee.end_date - attachee.start_date).days
    duration_weeks = duration_days // 7

    buffer = io.BytesIO()
    p = canvas.Canvas(buffer, pagesize=A4)
    draw_header_and_border(p)

    y_title, y_start = 9.2*inch, 8.9*inch
    p.setFont("Helvetica-Bold", 13)
    p.drawCentredString(4.15*inch, y_title, "CERTIFICATE OF COMPLETION")

    p.setFont("Helvetica", 11)
    p.drawString(0.8*inch, y_start, f"Date: {timezone.now().strftime('%d %b %Y')}")
    p.drawString(0.8*inch, y_start - 0.2*inch, f"Ref: {attachee.tracking_id}")

    p.setFont("Helvetica-Bold", 11)
    p.drawString(0.8*inch, y_start - 0.6*inch, "TO WHOM IT MAY CONCERN,")

    p.setFont("Helvetica", 11)
    full_name = f"{attachee.first_name.upper()} {attachee.last_name.upper()}"

    paras = [
        (
            f"This letter serves to formally certify that {full_name}, a student "
            f"from {attachee.institution}, has successfully completed {poss} "
            f"comprehensive industrial attachment at EUJIM SOLUTIONS LIMITED. "
            f"The program ran from {attachee.start_date.strftime('%d %b %Y')} "
            f"to {attachee.end_date.strftime('%d %b %Y')}, totaling "
            f"{duration_weeks} weeks of professional engagement under "
            f"Reference No: {attachee.tracking_id}."
        ),
        (
            f"During this tenure, {attachee.first_name} was fully integrated "
            f"into our technical operations, specifically focusing on "
            f"Software Development, ICT Consultancy, and Web Design. "
            f"{subj} demonstrated an exceptional work ethic, showing great "
            f"initiative in problem-solving and execution. {subj} proved to "
            f"be a disciplined, reliable, and technically competent individual "
            f"who consistently maintained high-quality standards."
        ),
        (
            f"This certificate recognizes the successful completion of all "
            f"attachment requirements. We highly appreciate the contribution "
            f"{attachee.first_name} made to our team and we wish {obj} "
            f"continued success in {poss} academic and professional future. "
            f"For further verification, contact info@eujimsolutions.com."
        )
    ]

    y = y_start - 1.0*inch
    for txt in paras:
        to = p.beginText(0.8*inch, y)
        to.setLeading(14)
        wrapped = textwrap.wrap(txt, width=90)
        for line in wrapped:
            to.textLine(line)
        p.drawText(to)
        y -= (len(wrapped) * 14) + 20

    draw_footer(p, attachee, y - 0.2*inch)
    p.showPage()
    p.save()
    buffer.seek(0)
    return FileResponse(
        buffer, as_attachment=False, content_type='application/pdf',
        filename=f'Completion_{attachee.tracking_id}.pdf'
    )


def download_recommendation_letter(request, attachee_id):
    attachee = get_object_or_404(Attachee, id=attachee_id)

    is_male = attachee.gender.lower() == 'male'
    subj = "He" if is_male else "She"
    poss = "his" if is_male else "her"
    obj = "him" if is_male else "her"

    duration_days = (attachee.end_date - attachee.start_date).days
    duration_weeks = duration_days // 7

    buffer = io.BytesIO()
    p = canvas.Canvas(buffer, pagesize=A4)
    draw_header_and_border(p)

    y_title, y_start = 9.2*inch, 8.9*inch
    p.setFont("Helvetica-Bold", 13)
    p.drawCentredString(4.15*inch, y_title, "RECOMMENDATION LETTER")

    p.setFont("Helvetica", 11)
    p.drawString(0.8*inch, y_start, f"Date: {timezone.now().strftime('%d %b %Y')}")
    p.drawString(0.8*inch, y_start - 0.2*inch, f"Ref: {attachee.tracking_id}")

    p.setFont("Helvetica-Bold", 11)
    p.drawString(0.8*inch, y_start - 0.6*inch, "TO WHOM IT MAY CONCERN,")

    p.setFont("Helvetica", 11)
    full_name = f"{attachee.first_name.upper()} {attachee.last_name.upper()}"

    paras = [
        (
            f"It is a pleasure to recommend {full_name} for professional roles. "
            f"{subj} completed a rigorous {duration_weeks}-week industrial "
            f"attachment at EUJIM SOLUTIONS where {subj.lower()} made a lasting "
            f"impression under Reference No: {attachee.tracking_id}. During "
            f"{poss} time with us, {attachee.first_name} demonstrated "
            f"exceptional skills, dedication, and a passion for learning."
        ),
        (
            f"As an attachee, {attachee.first_name} worked closely with our "
            f"teams in software development, digital marketing, web design, "
            f"and ICT consultancy. {subj} showed a remarkable ability to "
            f"quickly adapt to new tasks and responsibilities, collaborating "
            f"effectively with colleagues and making significant contributions "
            f"to various projects. Throughout the attachment, {subj.lower()} "
            f"demonstrated a strong work ethic, a willingness to learn, and "
            f"a commitment to delivering high-quality results."
        ),
        (
            f"I highly recommend {full_name} for any future opportunities. "
            f"{subj} has the skills, knowledge, and attitude necessary to "
            f"excel in {poss} chosen career path. If you have any further "
            f"questions, please do not hesitate to contact us through our "
            f"email info@eujimsolutions.com or call us at 0113281424."
        )
    ]

    y = y_start - 1.0*inch
    for txt in paras:
        to = p.beginText(0.8*inch, y)
        to.setLeading(14)
        wrapped = textwrap.wrap(txt, width=90)
        for line in wrapped:
            to.textLine(line)
        p.drawText(to)
        y -= (len(wrapped) * 14) + 20

    draw_footer(p, attachee, y - 0.2*inch)
    p.showPage()
    p.save()
    buffer.seek(0)
    return FileResponse(
        buffer, as_attachment=False, content_type='application/pdf',
        filename=f'Recommendation_{attachee.tracking_id}.pdf'
    )


def download_gate_pass(request, attachee_id):
    attachee = get_object_or_404(Attachee, id=attachee_id)
    buffer = io.BytesIO()
    p = canvas.Canvas(buffer, pagesize=A4)
    draw_header_and_border(p)
    
    y_title, y_section1 = 9.2*inch, 8.7*inch
    p.setFont("Helvetica-Bold", 15)
    title = f"OFFICIAL GATE PASS ({attachee.tracking_id})"
    p.drawCentredString(4.15*inch, y_title, title)
    
    # Section 1: APPLICANT DETAILS
    p.setFont("Helvetica-Bold", 12)
    p.drawString(1.0*inch, y_section1, "APPLICANT DETAILS")
    p.line(1.0*inch, y_section1 - 0.05*inch, 3.2*inch, y_section1 - 0.05*inch)
    
    p.setFont("Helvetica", 11)
    details = [
        f"Full Name: {attachee.first_name} {attachee.last_name}",
        f"Phone Number: {attachee.phone}",
        f"National ID: {attachee.national_id_number}",
        f"Gender: {attachee.gender}",
        f"Institution: {attachee.institution}",
        f"Reference No: {attachee.tracking_id}",
        f"Duration: {attachee.start_date.strftime('%d %b %Y')} to {attachee.end_date.strftime('%d %b %Y')}"
    ]
    
    curr_y = y_section1 - 0.35*inch
    for item in details:
        p.drawString(1.0*inch, curr_y, item)
        curr_y -= 0.22*inch  # Added vertical space between lines
        
    # Section 2: TERMS OF ENGAGEMENT (Added more top margin)
    y_section2 = curr_y - 0.4*inch 
    p.setFont("Helvetica-Bold", 12)
    p.drawString(1.0*inch, y_section2, "TERMS OF ENGAGEMENT")
    p.line(1.0*inch, y_section2 - 0.05*inch, 3.5*inch, y_section2 - 0.05*inch)
    
    welcome_text = (
        f"We welcome you, {attachee.first_name}, to EUJIM SOLUTIONS LIMITED. "
        "During the stated period, you will be integrated into our professional team. "
        "You are required to report to the office from Monday to Friday, between "
        "9:00 AM and 4:00 PM. Please maintain high levels of discipline and "
        "adhere to all company policies throughout your industrial attachment."
    )
    
    p.setFont("Helvetica", 11)
    to = p.beginText(1.0*inch, y_section2 - 0.35*inch)
    to.setLeading(16)  # Better line spacing for readability
    wrapped = textwrap.wrap(welcome_text, width=85)
    for line in wrapped:
        to.textLine(line)
    p.drawText(to)
    
    # Footer Positioning
    draw_footer(p, attachee, y_section2 - 2.5*inch)
    
    p.showPage()
    p.save()
    buffer.seek(0)
    return FileResponse(
        buffer, as_attachment=False, content_type='application/pdf',
        filename=f'Pass_{attachee.tracking_id}.pdf'
    )


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
    name_str = f"{attachee.first_name} {attachee.last_name}"
    p.drawCentredString(1.68*inch, 1.4*inch, name_str)
    p.setFont("Helvetica", 7)

    p.drawString(0.2*inch, 1.15*inch, f"ID NO: {attachee.national_id_number}")
    p.drawString(0.2*inch, 1.0*inch, f"PHONE: {attachee.phone}")
    p.drawString(0.2*inch, 0.85*inch, f"EMAIL: {attachee.email}")
    p.drawString(0.2*inch, 0.7*inch, f"REF NO: {attachee.tracking_id}")
    p.drawString(0.2*inch, 0.55*inch, f"INST: {attachee.institution}")

    p.setFillColorRGB(0.8, 0.1, 0.1)
    p.setFont("Helvetica-Bold", 6.5)
    valid_text = (
        f"VALID: {attachee.start_date.strftime('%b %Y')} - "
        f"{attachee.end_date.strftime('%b %Y')}"
    )
    p.drawCentredString(1.68*inch, 0.3*inch, valid_text)

    qr_data = f"REF:{attachee.tracking_id} | {attachee.first_name}"
    qr = qrcode.make(qr_data)
    qb = io.BytesIO()
    qr.save(qb, format='PNG')
    qb.seek(0)
    p.drawImage(
        ImageReader(qb), 2.5*inch, 0.5*inch, width=0.7*inch, height=0.7*inch
    )
    p.showPage()
    p.save()
    buffer.seek(0)
    return FileResponse(
        buffer, as_attachment=False, content_type='application/pdf',
        filename=f'ID_{attachee.tracking_id}.pdf'
    )


@user_passes_test(is_admin)
def approve_student(request, attachee_id):
    attachee = get_object_or_404(Attachee, id=attachee_id)
    attachee.status = 'Approved'
    attachee.save()
    messages.success(request, f"Approved {attachee.first_name}.")
    return redirect('dashboard')


@user_passes_test(is_admin)
def reject_student(request, attachee_id):
    attachee = get_object_or_404(Attachee, id=attachee_id)
    attachee.status = 'Rejected'
    attachee.save()
    messages.error(request, f"Rejected {attachee.first_name}.")
    return redirect('dashboard')


@user_passes_test(is_admin)
def university_analytics(request):
    stats = Attachee.objects.values('institution').annotate(
        student_count=Count('id')).order_by('-student_count')
    gender_stats = Attachee.objects.values('gender').annotate(
        count=Count('id'))
    return render(
        request, 'accounts/analytics.html',
        {
            'stats': stats,
            'gender_stats': gender_stats,
            'total_students': Attachee.objects.count()
        }
    )


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
    return render(
        request, 'accounts/submit_feedback.html', {'attachee': attachee}
    )