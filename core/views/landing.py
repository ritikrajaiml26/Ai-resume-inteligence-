from django.urls import path
from django.http import HttpResponse

def landing_view(request):
    return HttpResponse("Welcome to AI Resume Intelligence Platform")

urlpatterns = [
    path('', landing_view, name='landing'),
]
