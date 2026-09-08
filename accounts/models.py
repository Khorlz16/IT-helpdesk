import os

from django.contrib.auth.models import AbstractUser
from django.core.exceptions import ValidationError
from django.core.validators import FileExtensionValidator
from django.db import models

MAX_AVATAR_SIZE = 2 * 1024 * 1024


def validate_avatar_image(value):
    extension = os.path.splitext(value.name)[1].lower().lstrip('.')
    allowed_extensions = {'jpg', 'jpeg', 'png', 'webp'}

    if extension not in allowed_extensions:
        raise ValidationError('Avatar must be a JPG, PNG, or WEBP image.')

    if value.size > MAX_AVATAR_SIZE:
        raise ValidationError('Avatar must be 2MB or smaller.')


class Department(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)

    def __str__(self):
        return self.name

class Branch(models.Model):
    name = models.CharField(max_length=100, unique=True)
    code = models.CharField(max_length=10, unique=True)
    location = models.CharField(max_length=200, blank=True)

    def __str__(self):
        return self.name

class User(AbstractUser):
    class Role(models.TextChoices):
        EMPLOYEE = 'EMPLOYEE', 'Employee'
        IT_STAFF = 'IT_STAFF', 'IT Staff'
        IT_ADMIN = 'IT_ADMIN', 'IT Admin'

    pzc = models.CharField(max_length=50, unique=True, blank=False, null=False, db_index=True)
    role = models.CharField(
        max_length=20,
        choices=Role.choices,
        default=Role.EMPLOYEE,
    )
    department = models.ForeignKey(
        Department,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='users'
    )
    branch = models.ForeignKey(
        Branch,
        on_delete=models.PROTECT,
        null=False,
        blank=False,
        related_name='users'
    )
    is_central_admin = models.BooleanField(default=False)
    job_title = models.CharField(max_length=100, blank=True)
    company_email = models.EmailField(blank=True)
    avatar = models.ImageField(
        upload_to='avatars/%Y/%m/',
        blank=True,
        null=True,
        validators=[
            FileExtensionValidator(allowed_extensions=['jpg', 'jpeg', 'png', 'webp']),
            validate_avatar_image,
        ],
        help_text='Upload a profile image up to 2MB (JPG, PNG, or WEBP).'
    )
    must_change_password = models.BooleanField(default=True)

    USERNAME_FIELD = 'pzc'
    REQUIRED_FIELDS = ['username']  # keep username as required but not for login

    def __str__(self):
        return f"{self.get_full_name()} ({self.pzc})"

    @property
    def is_employee(self):
        return self.role == self.Role.EMPLOYEE

    @property
    def is_it_staff(self):
        return self.role == self.Role.IT_STAFF

    @property
    def is_it_admin(self):
        return self.role == self.Role.IT_ADMIN

    @property
    def role_label(self):
        if self.is_central_admin:
            return 'IT Central Admin'
        return self.get_role_display()
