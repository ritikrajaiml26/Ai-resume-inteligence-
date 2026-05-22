from django.urls import path
from . import views

app_name = 'resumes'

urlpatterns = [
    path('create/', views.resume_create, name='resume_create'),
    path('manual/', views.manual_builder, name='manual_builder'),
    path('<int:pk>/', views.resume_detail, name='resume_detail'),
    path('<int:pk>/preview/<str:template_style>/', views.resume_preview, name='resume_preview'),
    path('<int:pk>/download/<str:template_style>/', views.download_resume_pdf, name='resume_download'),
    path('<int:pk>/chat/', views.resume_chat, name='resume_chat'),
]
