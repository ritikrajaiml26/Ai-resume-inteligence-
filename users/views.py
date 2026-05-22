from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import PasswordResetView, PasswordResetConfirmView
from django.shortcuts import render, redirect
from django.urls import reverse_lazy
from .forms import RegisterForm, LoginForm, ProfileUpdateForm, CustomPasswordResetForm, CustomSetPasswordForm
from resumes.models import Resume


def landing_page(request):
    return render(request, 'landing.html')


def register_view(request):
    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect('users:dashboard')
    else:
        form = RegisterForm()
    return render(request, 'users/register.html', {'form': form})


def login_view(request):
    if request.method == 'POST':
        form = LoginForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            return redirect('users:dashboard')
    else:
        form = LoginForm()
    return render(request, 'users/login.html', {'form': form})


def logout_view(request):
    logout(request)
    return redirect('users:login')


def admin_login_view(request):
    if request.method == 'POST':
        form = LoginForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            if user.is_staff or user.is_superuser:
                login(request, user)
                return redirect('/admin/')
            form.add_error(None, 'This account does not have admin access.')
    else:
        form = LoginForm()
    return render(request, 'users/admin_login.html', {'form': form})


class CustomPasswordResetView(PasswordResetView):
    template_name = 'users/password_reset.html'
    email_template_name = 'users/password_reset_email.html'
    success_url = reverse_lazy('users:password_reset_done')
    form_class = CustomPasswordResetForm


class CustomPasswordResetConfirmView(PasswordResetConfirmView):
    template_name = 'users/password_reset_confirm.html'
    success_url = reverse_lazy('users:login')
    form_class = CustomSetPasswordForm


@login_required
def profile_view(request):
    if request.method == 'POST':
        form = ProfileUpdateForm(request.POST, instance=request.user)
        if form.is_valid():
            form.save()
            return redirect('users:profile')
    else:
        form = ProfileUpdateForm(instance=request.user)
    return render(request, 'users/profile.html', {'form': form})


@login_required
def dashboard_view(request):
    resumes = Resume.objects.filter(user=request.user).order_by('-created_at')[:5]
    latest_resume = resumes.first() if resumes else None
    stats = {
        'resume_count': Resume.objects.filter(user=request.user).count(),
        'recent_ats': resumes.count(),
    }
    return render(request, 'users/dashboard.html', {
        'resumes': resumes,
        'stats': stats,
        'latest_resume': latest_resume,
    })
