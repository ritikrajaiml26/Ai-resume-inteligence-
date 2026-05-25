from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm, PasswordResetForm, SetPasswordForm
from django.contrib.auth.models import User


class RegisterForm(UserCreationForm):
    full_name = forms.CharField(widget=forms.TextInput(attrs={
        'class': 'input-field',
        'placeholder': 'Full name',
    }), required=True)
    username = forms.CharField(widget=forms.TextInput(attrs={
        'class': 'input-field',
        'placeholder': 'Username',
    }))
    email = forms.EmailField(required=True, widget=forms.EmailInput(attrs={
        'class': 'input-field',
        'placeholder': 'Email',
    }))
    password1 = forms.CharField(widget=forms.PasswordInput(attrs={
        'class': 'input-field',
        'placeholder': 'Password',
    }))
    password2 = forms.CharField(widget=forms.PasswordInput(attrs={
        'class': 'input-field',
        'placeholder': 'Confirm password',
    }))

    class Meta:
        model = User
        fields = ['full_name', 'username', 'email', 'password1', 'password2']

    def save(self, commit=True):
        user = super().save(commit=False)
        full_name = self.cleaned_data.get('full_name', '').strip()
        if full_name:
            name_parts = full_name.split()
            user.first_name = name_parts[0]
            user.last_name = ' '.join(name_parts[1:]) if len(name_parts) > 1 else ''
        if commit:
            user.save()
        return user


class ProfileUpdateForm(forms.ModelForm):
    full_name = forms.CharField(widget=forms.TextInput(attrs={
        'class': 'input-field',
        'placeholder': 'Full name',
    }), required=True)

    class Meta:
        model = User
        fields = ['full_name', 'username', 'email']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance:
            self.fields['full_name'].initial = f"{self.instance.first_name} {self.instance.last_name}".strip()

    def clean_username(self):
        username = self.cleaned_data.get('username')
        user_qs = User.objects.filter(username=username).exclude(pk=self.instance.pk)
        if user_qs.exists():
            raise forms.ValidationError('This username is already taken.')
        return username

    def clean_email(self):
        email = self.cleaned_data.get('email')
        email_qs = User.objects.filter(email=email).exclude(pk=self.instance.pk)
        if email_qs.exists():
            raise forms.ValidationError('This email is already registered.')
        return email

    def save(self, commit=True):
        user = super().save(commit=False)
        full_name = self.cleaned_data.get('full_name', '').strip()
        name_parts = full_name.split()
        user.first_name = name_parts[0] if name_parts else ''
        user.last_name = ' '.join(name_parts[1:]) if len(name_parts) > 1 else ''
        if commit:
            user.save()
        return user


class LoginForm(AuthenticationForm):
    username = forms.CharField(
        label="Username or Email",
        widget=forms.TextInput(attrs={
            'class': 'input-field',
            'placeholder': 'Username or Email',
            'autofocus': True
        })
    )
    password = forms.CharField(
        label="Password",
        widget=forms.PasswordInput(attrs={
            'class': 'input-field',
            'placeholder': 'Password'
        })
    )


class CustomPasswordResetForm(PasswordResetForm):
    email = forms.EmailField(widget=forms.EmailInput(attrs={'class': 'input-field', 'placeholder': 'Email'}))


class CustomSetPasswordForm(SetPasswordForm):
    new_password1 = forms.CharField(widget=forms.PasswordInput(attrs={'class': 'input-field', 'placeholder': 'New password'}))
    new_password2 = forms.CharField(widget=forms.PasswordInput(attrs={'class': 'input-field', 'placeholder': 'Confirm new password'}))
