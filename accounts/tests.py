from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model
from .models import Department, Branch

User = get_user_model()

class UserModelTests(TestCase):
    def setUp(self):
        self.department = Department.objects.create(name='IT')
        self.branch = Branch.objects.create(name='HQ', code='HQ')

    def test_create_user_with_roles(self):
        emp = User.objects.create_user(
            pzc='PZC1001', username='employee1', password='temp12345',
            role=User.Role.EMPLOYEE, department=self.department, branch=self.branch
        )
        self.assertTrue(emp.is_employee)
        self.assertFalse(emp.is_it_staff)
        self.assertFalse(emp.is_it_admin)

        staff = User.objects.create_user(
            pzc='PZC2001', username='staff1', password='temp12345',
            role=User.Role.IT_STAFF, branch=self.branch
        )
        self.assertTrue(staff.is_it_staff)

        admin = User.objects.create_user(
            pzc='PZC3001', username='admin1', password='temp12345',
            role=User.Role.IT_ADMIN, branch=self.branch
        )
        self.assertTrue(admin.is_it_admin)

    def test_must_change_password_default(self):
        user = User.objects.create_user(pzc='PZC9999', username='user', password='temp12345', branch=self.branch)
        self.assertTrue(user.must_change_password)

class AuthenticationFlowTests(TestCase):
    def test_login_with_pzc(self):
        branch = Branch.objects.create(name='Branch A', code='BRA')
        user = User.objects.create_user(
            pzc='PZCLOGIN', username='loginuser', password='temp12345',
            must_change_password=False, branch=branch
        )
        response = self.client.post(reverse('accounts:login'), {
            'username': 'PZCLOGIN',
            'password': 'temp12345'
        })
        self.assertRedirects(response, reverse('requests:dashboard'))
