from django.db import models
from django.utils import timezone
import datetime

class Attachee(models.Model):
    # UPDATED: Added 'In-Progress' to the status lifecycle
    STATUS_CHOICES = [
        ('Pending', 'Pending'),
        ('Approved', 'Approved'),
        ('In-Progress', 'In-Progress'),
        ('Rejected', 'Rejected'),
        ('Completed', 'Completed'),
    ]

    # Personal Information
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    national_id_number = models.CharField(max_length=20, unique=True)
    email = models.EmailField()
    phone = models.CharField(max_length=15)
    gender = models.CharField(max_length=10) 
    institution = models.CharField(max_length=200) 
    
    # FIX: We add this back as nullable to stop the "NOT NULL" database crash
    date_of_birth = models.DateField(null=True, blank=True)
    
    # Attachment Details
    start_date = models.DateField()
    end_date = models.DateField()
    
    # Documents
    id_document = models.FileField(upload_to='documents/ids/')
    intro_letter = models.FileField(upload_to='documents/letters/')
    curriculum_vitae = models.FileField(upload_to='documents/cvs/')
    signed_contract = models.FileField(upload_to='contracts/signed/', null=True, blank=True)
    
    # Declaration & Consent
    data_policy_consent = models.BooleanField(default=False)
    terms_consent = models.BooleanField(default=False)
    marketing_consent = models.BooleanField(default=False)
    
    # Status and Completion
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Pending')
    
    # NEW: Admin Decision Hub Notes
    admin_notes = models.TextField(blank=True, null=True, help_text="Internal notes regarding the application.")
    
    completion_date = models.DateField(null=True, blank=True)
    tracking_id = models.CharField(max_length=20, unique=True, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        if not self.tracking_id:
            year = datetime.datetime.now().year
            last_id = Attachee.objects.all().count() + 1
            self.tracking_id = f"EUJ-{year}-{last_id:03d}"
        super().save(*args, **kwargs)

    def days_remaining(self):
        """Calculates days until attachment ends for the dashboard"""
        if self.end_date:
            today = timezone.now().date()
            remaining = (self.end_date - today).days
            return max(0, remaining)
        return 0

    def __str__(self):
        return f"{self.first_name} {self.last_name} ({self.tracking_id})"

class Evaluation(models.Model):
    attachee = models.OneToOneField(Attachee, on_delete=models.CASCADE, related_name='evaluation')
    technical_competence = models.IntegerField(default=0) # Scale 1-5
    discipline = models.IntegerField(default=0)
    teamwork = models.IntegerField(default=0)
    comments = models.TextField(blank=True, null=True)
    evaluated_at = models.DateTimeField(auto_now_add=True)

    def average_score(self):
        return round((self.technical_competence + self.discipline + self.teamwork) / 3, 1)

class StudentFeedback(models.Model):
    attachee = models.OneToOneField(Attachee, on_delete=models.CASCADE, related_name='student_feedback')
    mentorship_quality = models.IntegerField(default=3) # Scale 1-5
    environment_rating = models.IntegerField(default=3)
    resource_availability = models.IntegerField(default=3)
    student_comments = models.TextField(blank=True, null=True)
    submitted_at = models.DateTimeField(auto_now_add=True)

    def overall_satisfaction(self):
        return round((self.mentorship_quality + self.environment_rating + self.resource_availability) / 3, 1)