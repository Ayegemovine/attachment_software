from django import forms
from .models import Attachee
from django.core.exceptions import ValidationError

class AttacheeForm(forms.ModelForm):
    # Fixed Gender Selection with explicit choices
    GENDER_CHOICES = [
        ('', 'Select Gender'),
        ('Male', 'Male'),
        ('Female', 'Female'),
        ('Other', 'Other'),
    ]
    gender = forms.ChoiceField(
        choices=GENDER_CHOICES, 
        widget=forms.Select(attrs={'class': 'form-select custom-input'}),
        help_text="Please select your gender from the list."
    )

    class Meta:
        model = Attachee
        fields = [
            'first_name', 'last_name', 'national_id_number', 'email', 'phone', 
            'gender', 'institution', # date_of_birth removed
            'start_date', 'end_date',  
            'id_document', 'intro_letter', 'curriculum_vitae', 'signed_contract', 
            'data_policy_consent', 'terms_consent', 'marketing_consent'
        ]
        
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'form-control custom-input', 'placeholder': 'Enter your first name'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control custom-input', 'placeholder': 'Enter your last name'}),
            'national_id_number': forms.TextInput(attrs={'class': 'form-control custom-input', 'placeholder': 'ID or Passport Number'}),
            'email': forms.EmailInput(attrs={'class': 'form-control custom-input', 'placeholder': 'email@example.com'}),
            'phone': forms.TextInput(attrs={'class': 'form-control custom-input', 'placeholder': '+254...'}),
            
            # Start and End Date Pickers
            'start_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control custom-input'}),
            'end_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control custom-input'}),
            
            'institution': forms.TextInput(attrs={'class': 'form-control custom-input', 'placeholder': 'University/College Name'}),
            'id_document': forms.FileInput(attrs={'class': 'form-control form-control-sm', 'accept': 'application/pdf,image/*'}),
            'intro_letter': forms.FileInput(attrs={'class': 'form-control form-control-sm', 'accept': 'application/pdf,.docx'}),
            'curriculum_vitae': forms.FileInput(attrs={'class': 'form-control form-control-sm', 'accept': 'application/pdf,.docx'}),
            'signed_contract': forms.FileInput(attrs={'class': 'form-control form-control-sm', 'accept': 'application/pdf'}),
            
            'data_policy_consent': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'terms_consent': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'marketing_consent': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def clean(self):
        """Validation to ensure attachment dates are logical"""
        cleaned_data = super().clean()
        start_date = cleaned_data.get("start_date")
        end_date = cleaned_data.get("end_date")

        if start_date and end_date:
            if end_date < start_date:
                raise ValidationError("The attachment end date cannot be earlier than the start date.")
        return cleaned_data

    def clean_signed_contract(self):
        """Strict validation to ensure the contract is a PDF and under 7MB"""
        contract = self.cleaned_data.get('signed_contract')
        if contract:
            if not contract.name.endswith('.pdf'):
                raise ValidationError("The signed contract must be in PDF format.")
            if contract.size > 7 * 1024 * 1024:
                raise ValidationError("The file size must not exceed 7MB.")
        return contract

    def __init__(self, *args, **kwargs):
        super(AttacheeForm, self).__init__(*args, **kwargs)
        self.fields['id_document'].label = "National ID / Passport"
        self.fields['id_document'].help_text = "Purpose: Identification. Format: PDF, JPG, or PNG. Max size: 7MB."
        
        self.fields['intro_letter'].label = "Institutional Introduction Letter"
        self.fields['intro_letter'].help_text = "Purpose: Official introduction from school. Format: PDF or DOCX. Max size: 7MB."
        
        self.fields['curriculum_vitae'].label = "Curriculum Vitae (CV)"
        self.fields['curriculum_vitae'].help_text = "Purpose: Professional background. Format: PDF or DOCX. Max size: 7MB."
        
        self.fields['signed_contract'].label = "Signed Engagement Contract"
        self.fields['signed_contract'].help_text = "Purpose: Legal agreement for free engagement & data usage. Format: Strictly PDF. Max size: 7MB."
        
        self.fields['start_date'].label = "Proposed Start Date"
        self.fields['end_date'].label = "Proposed End Date"