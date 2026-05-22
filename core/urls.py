from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include('api.urls')),
    path('users/', include('users.urls')),
    path('resumes/', include('resumes.urls')),
    path('ats/', include('ats.urls')),
    path('ai/', include('ai_engine.urls')),
    path('', include('users.urls')),  # landing + auth at root
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
