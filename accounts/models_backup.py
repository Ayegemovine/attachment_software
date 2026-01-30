from django.db import models
import uuid
from django.core.validators import FileExtensionValidator

class Attachee(models.Model):
    # Personal Information
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    other_name = models.CharField(max_length=100, blank=True, null=True)
    email = models.EmailField(unique=True)
    phone = models.CharField(max_length=20)
    date_of_birth = models.DateField(blank=True, null=True)
    gender = models.CharField(max_length=10, choices=[
        ('male', 'Male'),
        ('female', 'Female'),
        ('other', 'Other')
    ], blank=True, null=True)
    nationality = models.CharField(max_length=100, blank=True, null=True)
    id_number = models.CharField(max_length=50, blank=True, null=True)
    address = models.TextField(blank=True, null=True)
    
    # Educational Information
    institution = models.CharField(max_length=200)
    department = models.CharField(max_length=200)
    course = models.CharField(max_length=200, blank=True, null=True)
    student_id = models.CharField(max_length=50, blank=True, null=True)
    year_of_study = models.CharField(max_length=50, blank=True, null=True)
    expected_graduation_date = models.DateField(blank=True, null=True)
    
    # Document Uploads
    curriculum_vitae = models.FileField(
        upload_to='attachees/cvs/%Y/%m/%d/',
        validators=[FileExtensionValidator(['pdf', 'doc', 'docx'])]
    )
    id_document = models.FileField(
        upload_to='attachees/id_documents/%Y/%m/%d/',
        validators=[FileExtensionValidator(['pdf', 'jpg', 'jpeg', 'png'])]
    )
    academic_transcript = models.FileField(blank=True, null=True, 
        upload_to='attachees/transcripts/%Y/%m/%d/',
        validators=[FileExtensionValidator(['pdf', 'jpg', 'jpeg', 'png'])],
        blank=True,
        null=True
    )
    certificate = models.FileField(blank=True, null=True, 
        upload_to='attachees/certificates/%Y/%m/%d/',
        validators=[FileExtensionValidator(['pdf', 'jpg', 'jpeg', 'png'])],
        blank=True,
        null=True
    )
    school_letter = models.FileField(blank=True, null=True, 
        upload_to='attachees/school_letters/%Y/%m/%d/',
        validators=[FileExtensionValidator(['pdf', 'doc', 'docx'])],
        blank=True,
        null=True
    )
    photo = models.FileField(blank=True, null=True, 
        upload_to='attachees/photos/%Y/%m/%d/',
        validators=[FileExtensionValidator(['jpg', 'jpeg', 'png'])],
        blank=True,
        null=True
    )
    signature = models.FileField(blank=True, null=True, 
        upload_to='attachees/signatures/%Y/%m/%d/',
        validators=[FileExtensionValidator(['jpg', 'jpeg', 'png'])],
        blank=True,
        null=True
    )
    recommendation_letter = models.FileField(blank=True, null=True, 
        upload_to='attachees/recommendation_letters/%Y/%m/%d/',
        validators=[FileExtensionValidator(['pdf', 'doc', 'docx'])],
        blank=True,
        null=True
    )
    
    # Attachment Period
    start_date = models.DateField()
    end_date = models.DateField()
    
    # Application Details
    application_number = models.CharField(max_length=50, unique=True, blank=True, null=True)
    application_date = models.DateTimeField(auto_now_add=True)
    
    # Status Fields
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('under_review', 'Under Review'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ]
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    
    # Consent Fields
    consent_terms = models.BooleanField(default=False)
    consent_marketing = models.BooleanField(default=False)
    
    # Approval Fields
    is_approved = models.BooleanField(default=False)
    created_by_admin = models.BooleanField(default=False)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.first_name} {self.last_name} - {self.application_number}"
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Attachee'
        verbose_name_plural = 'Attachees'


# Optional: Attachment Opportunity Model for future use
class AttachmentOpportunity(models.Model):
    title = models.CharField(max_length=200)
    description = models.TextField()
    department = models.CharField(max_length=200)
    slots_available = models.IntegerField()
    start_date = models.DateField()
    end_date = models.DateField()
    requirements = models.TextField()
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return self.title
