from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User, Department, Branch

class UserAdmin(BaseUserAdmin):
    model = User
    list_display = ['pzc', 'username', 'get_full_name', 'role', 'department', 'branch', 'is_active', 'must_change_password']
    list_filter = ['role', 'is_active', 'must_change_password', 'department', 'branch']
    search_fields = ['pzc', 'username', 'first_name', 'last_name', 'company_email']
    ordering = ['pzc']
    fieldsets = (
        (None, {'fields': ('pzc', 'password')}),
        ('Personal info', {'fields': ('first_name', 'last_name', 'email', 'company_email', 'job_title')}),
        ('Permissions', {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('Important dates', {'fields': ('last_login', 'date_joined')}),
        ('Additional Info', {'fields': ('role', 'department', 'branch', 'must_change_password')}),
    )
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('pzc', 'username', 'password1', 'password2', 'role', 'department', 'branch', 'must_change_password'),
        }),
    )

admin.site.register(User, UserAdmin)
admin.site.register(Department)
admin.site.register(Branch)
