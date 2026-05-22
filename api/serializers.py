from rest_framework import serializers
from resumes.models import Resume, JobDescription, ATSAnalysis, GeneratedResume


class ResumeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Resume
        fields = ['id', 'title', 'summary', 'contact_email', 'contact_phone', 'linkedin_url', 'portfolio_url', 'template_style']


class JobDescriptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = JobDescription
        fields = ['id', 'title', 'description', 'required_skills', 'extracted_keywords']


class ATSAnalysisSerializer(serializers.ModelSerializer):
    class Meta:
        model = ATSAnalysis
        fields = ['score', 'keyword_match', 'missing_skills', 'weak_sections', 'suggestions', 'updated_at']


class GeneratedResumeSerializer(serializers.ModelSerializer):
    class Meta:
        model = GeneratedResume
        fields = ['id', 'template_style', 'content_html', 'created_at']
