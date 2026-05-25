from django import forms
from .models import Resume, JobDescription


class ResumeForm(forms.ModelForm):
    class Meta:
        model = Resume
        fields = ['full_name', 'title', 'summary', 'contact_email', 'contact_phone', 'linkedin_url', 'portfolio_url', 'template_style', 'resume_file']
        widgets = {
            'full_name': forms.TextInput(attrs={'class': 'input-field', 'placeholder': 'Your Full Name'}),
            'title': forms.TextInput(attrs={'class': 'input-field', 'placeholder': 'Resume title or target role'}),
            'summary': forms.Textarea(attrs={'class': 'input-field', 'placeholder': 'Professional summary', 'rows': 4}),
            'contact_email': forms.EmailInput(attrs={'class': 'input-field', 'placeholder': 'Email'}),
            'contact_phone': forms.TextInput(attrs={'class': 'input-field', 'placeholder': 'Phone'}),
            'linkedin_url': forms.URLInput(attrs={'class': 'input-field', 'placeholder': 'LinkedIn URL'}),
            'portfolio_url': forms.URLInput(attrs={'class': 'input-field', 'placeholder': 'Portfolio URL'}),
        }


class ManualResumeForm(forms.ModelForm):
    skills_raw = forms.CharField(required=False, widget=forms.Textarea(attrs={'class': 'input-field', 'placeholder': 'List skills separated by commas', 'rows': 3}))
    education_raw = forms.CharField(required=False, widget=forms.Textarea(attrs={'class': 'input-field', 'placeholder': 'Enter each education entry on a new line: Degree | Institution | Dates | Description', 'rows': 4}))
    experience_raw = forms.CharField(required=False, widget=forms.Textarea(attrs={'class': 'input-field', 'placeholder': 'Enter each experience on a new line: Role | Company | Duration | Location | Bullet details', 'rows': 5}))
    projects_raw = forms.CharField(required=False, widget=forms.Textarea(attrs={'class': 'input-field', 'placeholder': 'Enter each project on a new line: Title | Technologies | Description', 'rows': 4}))
    certifications_raw = forms.CharField(required=False, widget=forms.Textarea(attrs={'class': 'input-field', 'placeholder': 'Enter each certification on a new line: Title | Issuer | Year', 'rows': 3}))
    achievements_raw = forms.CharField(required=False, widget=forms.Textarea(attrs={'class': 'input-field', 'placeholder': 'Enter achievements on separate lines', 'rows': 3}))

    class Meta:
        model = Resume
        fields = ['full_name', 'title', 'summary', 'contact_email', 'contact_phone', 'linkedin_url', 'portfolio_url', 'template_style']
        widgets = {
            'full_name': forms.TextInput(attrs={'class': 'input-field', 'placeholder': 'Your Full Name'}),
            'title': forms.TextInput(attrs={'class': 'input-field', 'placeholder': 'Resume title or target role'}),
            'summary': forms.Textarea(attrs={'class': 'input-field', 'placeholder': 'Professional summary', 'rows': 4}),
            'contact_email': forms.EmailInput(attrs={'class': 'input-field', 'placeholder': 'Email'}),
            'contact_phone': forms.TextInput(attrs={'class': 'input-field', 'placeholder': 'Phone'}),
            'linkedin_url': forms.URLInput(attrs={'class': 'input-field', 'placeholder': 'LinkedIn URL'}),
            'portfolio_url': forms.URLInput(attrs={'class': 'input-field', 'placeholder': 'Portfolio URL'}),
        }


class JobDescriptionForm(forms.Form):
    description = forms.CharField(
        label="Job Description",
        widget=forms.Textarea(attrs={
            'class': 'input-field w-full rounded-2xl border border-slate-700 bg-slate-950 p-4 text-white focus:border-indigo-500 outline-none',
            'placeholder': 'Paste the job description here...',
            'rows': 6
        }),
        required=True
    )
    resume_file = forms.FileField(
        label="Upload Resume (PDF, DOCX, or TXT)",
        widget=forms.ClearableFileInput(attrs={
            'class': 'block w-full text-sm text-slate-400 file:mr-4 file:py-2.5 file:px-6 file:rounded-full file:border-0 file:text-sm file:font-semibold file:bg-indigo-600 file:text-white hover:file:bg-indigo-500 cursor-pointer file:cursor-pointer'
        }),
        required=True
    )
