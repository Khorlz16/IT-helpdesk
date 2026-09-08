from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm, UserChangeForm
from .models import User, Department, Branch

class PZCAuthenticationForm(AuthenticationForm):
    username = forms.CharField(
        label='',
        max_length=50,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter PZC',
            'autofocus': True,
        })
    )
    password = forms.CharField(
        label='',
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Password',
            'id': 'password-field',
        })
    )

class ProfileForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'department', 'branch', 'job_title', 'company_email', 'avatar']
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'form-control modern-field'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control modern-field'}),
            'department': forms.Select(attrs={'class': 'form-select modern-field'}),
            'branch': forms.Select(attrs={'class': 'form-select modern-field'}),
            'job_title': forms.TextInput(attrs={'class': 'form-control modern-field'}),
            'company_email': forms.EmailInput(attrs={'class': 'form-control modern-field'}),
            'avatar': forms.ClearableFileInput(attrs={'class': 'form-control modern-field', 'accept': 'image/*'}),
        }

class CustomUserCreationForm(UserCreationForm):
    is_central_admin = forms.BooleanField(required=False, widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}))

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ['pzc', 'username', 'first_name', 'last_name', 'role', 'department', 'branch', 'job_title', 'company_email', 'is_central_admin']
        widgets = {
            'pzc': forms.TextInput(attrs={'class': 'form-control modern-field'}),
            'username': forms.TextInput(attrs={'class': 'form-control modern-field'}),
            'first_name': forms.TextInput(attrs={'class': 'form-control modern-field'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control modern-field'}),
            'role': forms.Select(attrs={'class': 'form-select modern-field'}),
            'department': forms.Select(attrs={'class': 'form-select modern-field'}),
            'branch': forms.Select(attrs={'class': 'form-select modern-field'}),
            'job_title': forms.TextInput(attrs={'class': 'form-control modern-field'}),
            'company_email': forms.EmailInput(attrs={'class': 'form-control modern-field'}),
        }

class CustomUserChangeForm(UserChangeForm):
    password = None
    is_central_admin = forms.BooleanField(required=False, widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}))

    class Meta(UserChangeForm.Meta):
        model = User
        fields = ['pzc', 'username', 'first_name', 'last_name', 'role', 'department', 'branch', 'job_title', 'company_email', 'avatar', 'is_active', 'must_change_password', 'is_central_admin']
        widgets = {
            'pzc': forms.TextInput(attrs={'readonly': 'readonly', 'class': 'form-control modern-field'}),
            'username': forms.TextInput(attrs={'class': 'form-control modern-field'}),
            'first_name': forms.TextInput(attrs={'class': 'form-control modern-field'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control modern-field'}),
            'role': forms.Select(attrs={'class': 'form-select modern-field'}),
            'department': forms.Select(attrs={'class': 'form-select modern-field'}),
            'branch': forms.Select(attrs={'class': 'form-select modern-field'}),
            'job_title': forms.TextInput(attrs={'class': 'form-control modern-field'}),
            'company_email': forms.EmailInput(attrs={'class': 'form-control modern-field'}),
            'avatar': forms.ClearableFileInput(attrs={'class': 'form-control modern-field', 'accept': 'image/*'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'must_change_password': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

class UserPasswordResetForm(forms.Form):
    new_password1 = forms.CharField(label='New password', widget=forms.PasswordInput(attrs={'class': 'form-control modern-field'}))
    new_password2 = forms.CharField(label='Confirm new password', widget=forms.PasswordInput(attrs={'class': 'form-control modern-field'}))

    def clean(self):
        cleaned_data = super().clean()
        p1 = cleaned_data.get('new_password1')
        p2 = cleaned_data.get('new_password2')
        if p1 and p2 and p1 != p2:
            raise forms.ValidationError('Passwords do not match.')
        return cleaned_data
