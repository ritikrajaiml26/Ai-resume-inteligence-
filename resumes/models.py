from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()

class Resume(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='resumes')
    full_name = models.CharField(max_length=255, default='')
    title = models.CharField(max_length=255, default='My Resume')
    summary = models.TextField(blank=True)
    contact_email = models.EmailField(blank=True)
    contact_phone = models.CharField(max_length=50, blank=True)
    linkedin_url = models.URLField(blank=True)
    portfolio_url = models.URLField(blank=True)
    template_style = models.CharField(max_length=100, default='corporate')
    resume_file = models.FileField(upload_to='resumes/files/', null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    data = models.JSONField(default=dict, blank=True)

    def __str__(self):
        return f"{self.title} ({self.user.username})"

class Education(models.Model):
    resume = models.ForeignKey(Resume, on_delete=models.CASCADE, related_name='educations')
    institution = models.CharField(max_length=255)
    degree = models.CharField(max_length=255)
    field_of_study = models.CharField(max_length=255, blank=True)
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    description = models.TextField(blank=True)

class Skill(models.Model):
    resume = models.ForeignKey(Resume, on_delete=models.CASCADE, related_name='skills')
    name = models.CharField(max_length=100)
    proficiency = models.CharField(max_length=50, blank=True)  # optional

class Experience(models.Model):
    resume = models.ForeignKey(Resume, on_delete=models.CASCADE, related_name='experiences')
    company = models.CharField(max_length=255)
    role = models.CharField(max_length=255)
    location = models.CharField(max_length=255, blank=True)
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    description = models.TextField(blank=True)

class Project(models.Model):
    resume = models.ForeignKey(Resume, on_delete=models.CASCADE, related_name='projects')
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    link = models.URLField(blank=True)

class Certification(models.Model):
    resume = models.ForeignKey(Resume, on_delete=models.CASCADE, related_name='certifications')
    name = models.CharField(max_length=255)
    authority = models.CharField(max_length=255, blank=True)
    license_number = models.CharField(max_length=100, blank=True)
    url = models.URLField(blank=True)
    date_obtained = models.DateField(null=True, blank=True)

class Achievement(models.Model):
    resume = models.ForeignKey(Resume, on_delete=models.CASCADE, related_name='achievements')
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    date = models.DateField(null=True, blank=True)

class JobDescription(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='job_descriptions')
    title = models.CharField(max_length=255, blank=True)
    description = models.TextField()
    extracted_keywords = models.JSONField(default=list, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

class ATSAnalysis(models.Model):
    resume = models.ForeignKey(Resume, on_delete=models.CASCADE, related_name='ats_analyses')
    job_description = models.ForeignKey(JobDescription, on_delete=models.CASCADE, related_name='ats_analyses', null=True, blank=True)
    score = models.FloatField()
    keyword_match = models.FloatField(default=0.0)
    missing_keywords = models.JSONField(default=list, blank=True)
    weak_sections = models.JSONField(default=list, blank=True)
    project_impact_analysis = models.TextField(blank=True)
    suggestions = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

class GeneratedResume(models.Model):
    resume = models.ForeignKey(Resume, on_delete=models.CASCADE, related_name='generated_resumes')
    template_style = models.CharField(max_length=100)
    html_content = models.TextField(null=True, blank=True)
    content_html = models.TextField(null=True, blank=True) # Adding both to support existing code
    pdf_file = models.FileField(upload_to='resumes/pdfs/', null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    version = models.PositiveIntegerField(default=1)

    class Meta:
        unique_together = ('resume', 'version')

class ResumeVersion(models.Model):
    resume = models.ForeignKey(Resume, on_delete=models.CASCADE, related_name='versions')
    summary = models.TextField(blank=True)
    experience_data = models.JSONField(default=list, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
