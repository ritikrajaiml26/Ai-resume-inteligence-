from django.contrib import admin
from .models import Resume, Skill, Education, Experience, Project, Certification, Achievement, JobDescription, ATSAnalysis, GeneratedResume


@admin.register(Resume)
class ResumeAdmin(admin.ModelAdmin):
    list_display = ('title', 'user', 'updated_at')
    search_fields = ('title', 'user__username', 'summary')


class SkillInline(admin.TabularInline):
    model = Skill
    extra = 1


class EducationInline(admin.TabularInline):
    model = Education
    extra = 1


class ExperienceInline(admin.TabularInline):
    model = Experience
    extra = 1


class ProjectInline(admin.TabularInline):
    model = Project
    extra = 1


class CertificationInline(admin.TabularInline):
    model = Certification
    extra = 1


class AchievementInline(admin.TabularInline):
    model = Achievement
    extra = 1


@admin.register(JobDescription)
class JobDescriptionAdmin(admin.ModelAdmin):
    list_display = ('title', 'user', 'created_at')
    search_fields = ('title', 'description')


@admin.register(ATSAnalysis)
class ATSAnalysisAdmin(admin.ModelAdmin):
    list_display = ('resume', 'job_description', 'score', 'created_at')


@admin.register(GeneratedResume)
class GeneratedResumeAdmin(admin.ModelAdmin):
    list_display = ('resume', 'template_style', 'created_at')
