from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import PasswordChangeView, LoginView
from django.contrib.auth import logout
from django.urls import reverse_lazy
from django.core.exceptions import PermissionDenied
from django.db import models
from django.contrib import messages
from .models import User
from .forms import ProfileForm, PZCAuthenticationForm, CustomUserCreationForm, CustomUserChangeForm, UserPasswordResetForm

@login_required
def dashboard(request):
    return render(request, 'accounts/dashboard.html')

class CustomLoginView(LoginView):
    template_name = 'accounts/login.html'
    authentication_form = PZCAuthenticationForm

    def form_valid(self, form):
        response = super().form_valid(form)
        self.request.session.pop('notification_toast_seen', None)
        self.request.session.pop('toast_shown', None)
        self.request.session['show_notification_after_login'] = True
        return response

class CustomPasswordChangeView(PasswordChangeView):
    template_name = 'accounts/password_change.html'
    success_url = reverse_lazy('accounts:password_change_done')

    def form_valid(self, form):
        response = super().form_valid(form)
        self.request.user.must_change_password = False
        self.request.user.save()
        return response

def logout_view(request):
    logout(request)
    return redirect('accounts:login')

@login_required
def profile(request, user_id=None):
    if user_id:
        if not request.user.is_it_admin:
            raise PermissionDenied('Only super admins can view other profiles.')
        target_user = get_object_or_404(User, pk=user_id)
        if not request.user.is_central_admin and target_user.branch != request.user.branch:
            raise PermissionDenied('You can only view profiles in your branch.')
    else:
        target_user = request.user

    can_edit = request.user.is_it_admin and (
        request.user.is_central_admin or target_user.branch == request.user.branch
    )

    if request.method == 'POST' and can_edit:
        form = ProfileForm(request.POST, request.FILES, instance=target_user)
        if form.is_valid():
            if not request.user.is_central_admin:
                form.instance.branch = request.user.branch
            form.save()
            if user_id and target_user != request.user:
                return redirect('accounts:profile_user', user_id=target_user.pk)
            return redirect('accounts:profile')
    else:
        form = ProfileForm(instance=target_user) if can_edit else None

    context = {
        'profile_user': target_user,
        'form': form,
        'can_edit': can_edit,
    }
    return render(request, 'accounts/profile.html', context)

@login_required
def admin_user_list(request):
    if not request.user.is_it_admin:
        raise PermissionDenied('Only IT Admin can access account management.')
    q = request.GET.get('q', '').strip()
    users = User.objects.select_related('branch').all().order_by('pzc')
    if not request.user.is_central_admin:
        users = users.filter(branch=request.user.branch)
    if q:
        users = users.filter(
            models.Q(pzc__icontains=q) |
            models.Q(first_name__icontains=q) |
            models.Q(last_name__icontains=q) |
            models.Q(company_email__icontains=q)
        )
    return render(request, 'accounts/admin_user_list.html', {'users': users, 'q': q})

@login_required
def user_create(request):
    if not request.user.is_it_admin:
        raise PermissionDenied('Only IT Admin can create users.')
    if not request.user.is_central_admin:
        allowed_branch = request.user.branch
    else:
        allowed_branch = None

    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if not request.user.is_central_admin:
            form.fields['branch'].queryset = form.fields['branch'].queryset.filter(pk=allowed_branch.pk)
        if form.is_valid():
            user = form.save(commit=False)
            if not request.user.is_central_admin:
                user.branch = request.user.branch
                user.is_central_admin = False
            else:
                user.is_central_admin = form.cleaned_data.get('is_central_admin', False)
                if user.is_central_admin:
                    user.role = User.Role.IT_ADMIN
            user.must_change_password = True
            user.save()
            messages.success(request, f'User {user.pzc} created successfully.')
            return redirect('accounts:admin_user_list')
    else:
        form = CustomUserCreationForm()
        if not request.user.is_central_admin:
            form.fields['branch'].queryset = form.fields['branch'].queryset.filter(pk=allowed_branch.pk)
        else:
            form.fields['is_central_admin'].required = False
    return render(request, 'accounts/user_form.html', {'form': form, 'title': 'Create User'})

@login_required
def user_edit(request, user_id):
    if not request.user.is_it_admin:
        raise PermissionDenied('Only IT Admin can edit users.')
    target_user = get_object_or_404(User, pk=user_id)
    if not request.user.is_central_admin and target_user.branch != request.user.branch:
        raise PermissionDenied('You can only edit users from your branch.')
    if request.method == 'POST':
        form = CustomUserChangeForm(request.POST, instance=target_user)
        if not request.user.is_central_admin:
            form.fields['branch'].queryset = form.fields['branch'].queryset.filter(pk=request.user.branch.pk)
        if form.is_valid():
            user = form.save(commit=False)
            if not request.user.is_central_admin:
                user.branch = request.user.branch
                user.is_central_admin = False
            else:
                user.is_central_admin = form.cleaned_data.get('is_central_admin', False)
                if user.is_central_admin:
                    user.role = User.Role.IT_ADMIN
            user.save()
            messages.success(request, f'User {target_user.pzc} updated.')
            return redirect('accounts:admin_user_list')
    else:
        form = CustomUserChangeForm(instance=target_user)
        form.initial['is_central_admin'] = target_user.is_central_admin
        if not request.user.is_central_admin:
            form.fields['branch'].queryset = form.fields['branch'].queryset.filter(pk=request.user.branch.pk)
    return render(request, 'accounts/user_form.html', {'form': form, 'title': 'Edit User'})

@login_required
def user_toggle_active(request, user_id):
    if not request.user.is_it_admin:
        raise PermissionDenied('Only IT Admin can deactivate/reactivate users.')
    target_user = get_object_or_404(User, pk=user_id)
    if not request.user.is_central_admin and target_user.branch != request.user.branch:
        raise PermissionDenied('You can only manage users from your branch.')
    if target_user == request.user:
        messages.error(request, 'You cannot deactivate your own account.')
        return redirect('accounts:admin_user_list')
    if target_user.is_central_admin and target_user.is_active:
        active_central_admins = User.objects.filter(is_central_admin=True, is_active=True).exclude(pk=target_user.pk).count()
        if active_central_admins == 0:
            messages.error(request, 'At least one active central admin must remain.')
            return redirect('accounts:admin_user_list')
    target_user.is_active = not target_user.is_active
    target_user.save()
    status = 'activated' if target_user.is_active else 'deactivated'
    messages.success(request, f'User {target_user.pzc} {status}.')
    return redirect('accounts:admin_user_list')

@login_required
def user_delete(request, user_id):
    if not request.user.is_central_admin:
        raise PermissionDenied('Only central admin can delete accounts.')
    target_user = get_object_or_404(User, pk=user_id)
    if target_user == request.user:
        messages.error(request, 'You cannot delete your own account. Keep at least one active central admin account.')
        return redirect('accounts:admin_user_list')
    if target_user.is_central_admin:
        active_central_admins = User.objects.filter(is_central_admin=True, is_active=True).exclude(pk=target_user.pk).count()
        if active_central_admins == 0:
            messages.error(request, 'At least one active central admin must remain.')
            return redirect('accounts:admin_user_list')
    target_user.is_active = False
    target_user.save(update_fields=['is_active'])
    messages.success(request, f'Account {target_user.pzc} deactivated and archived.')
    return redirect('accounts:admin_user_list')

@login_required
def user_reset_password(request, user_id):
    if not request.user.is_it_admin:
        raise PermissionDenied('Only IT Admin can reset passwords.')
    target_user = get_object_or_404(User, pk=user_id)
    if not request.user.is_central_admin and target_user.branch != request.user.branch:
        raise PermissionDenied('You can only reset passwords for users in your branch.')
    if request.method == 'POST':
        form = UserPasswordResetForm(request.POST)
        if form.is_valid():
            target_user.set_password(form.cleaned_data['new_password1'])
            target_user.must_change_password = True
            target_user.save()
            messages.success(request, f'Password reset for {target_user.pzc}. User must change on next login.')
            return redirect('accounts:admin_user_list')
    else:
        form = UserPasswordResetForm()
    return render(request, 'accounts/password_reset_form.html', {'form': form, 'target_user': target_user})
