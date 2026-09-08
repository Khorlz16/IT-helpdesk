from django.test import TestCase
from django.utils import timezone
from datetime import timedelta
from django.core.exceptions import PermissionDenied
from django.contrib.auth import get_user_model
from accounts.models import Branch
from .models import Category, Request, RequestHistory, RequestUpdate, RequestItem
from .services import RequestService

User = get_user_model()

class RequestServiceTests(TestCase):
    def setUp(self):
        self.branch = Branch.objects.create(name='Ikeja', code='IKE')
        self.employee = User.objects.create_user(
            pzc='PZC100', username='emp', password='temp12345',
            role=User.Role.EMPLOYEE, branch=self.branch, must_change_password=False
        )
        self.staff = User.objects.create_user(
            pzc='PZC200', username='staff', password='temp12345',
            role=User.Role.IT_STAFF, branch=self.branch, must_change_password=False
        )
        self.admin = User.objects.create_user(
            pzc='PZC300', username='admin', password='temp12345',
            role=User.Role.IT_ADMIN, branch=self.branch, must_change_password=False
        )
        self.category = Category.objects.create(name='Hardware')

    def test_submit_request(self):
        req = RequestService.submit_request(
            employee=self.employee,
            category=self.category,
            description='Test request',
            requested_priority=Request.Priority.NORMAL,
        )
        self.assertEqual(req.status, Request.Status.PENDING)
        self.assertEqual(req.requester, self.employee)
        # history entry created
        self.assertTrue(RequestHistory.objects.filter(request=req, action='SUBMITTED').exists())

    def test_full_workflow(self):
        req = RequestService.submit_request(self.employee, self.category, 'Test', Request.Priority.NORMAL)
        RequestService.approve_request(self.admin, req)
        self.assertEqual(req.status, Request.Status.APPROVED)
        RequestService.assign_request(self.admin, req, self.staff)
        self.assertEqual(req.status, Request.Status.ASSIGNED)
        self.assertEqual(req.assigned_to, self.staff)
        RequestService.start_work(self.staff, req)
        self.assertEqual(req.status, Request.Status.IN_PROGRESS)
        RequestService.complete_work(self.staff, req, 'Fixed')
        self.assertEqual(req.status, Request.Status.COMPLETED)
        RequestService.close_request(self.admin, req)
        self.assertEqual(req.status, Request.Status.CLOSED)
        # history should contain all actions
        actions = list(RequestHistory.objects.filter(request=req).values_list('action', flat=True))
        self.assertIn('APPROVED', actions)
        self.assertIn('ASSIGNED', actions)
        self.assertIn('IN_PROGRESS', actions)
        self.assertIn('COMPLETED', actions)
        self.assertIn('CLOSED', actions)

    def test_only_admin_can_approve(self):
        req = RequestService.submit_request(self.employee, self.category, 'Test', Request.Priority.NORMAL)
        with self.assertRaises(PermissionDenied):
            RequestService.approve_request(self.employee, req)  # employee cannot approve

    def test_reopen_flow(self):
        req = RequestService.submit_request(self.employee, self.category, 'Test', Request.Priority.NORMAL)
        RequestService.approve_request(self.admin, req)
        RequestService.assign_request(self.admin, req, self.staff)
        RequestService.start_work(self.staff, req)
        RequestService.complete_work(self.staff, req, 'Done')
        RequestService.close_request(self.admin, req)
        # reopen within 72h
        RequestService.request_reopen(self.employee, req, 'Still broken')
        self.assertEqual(req.status, Request.Status.REOPEN_REQUESTED)
        RequestService.approve_reopen(self.admin, req)
        self.assertEqual(req.status, Request.Status.REOPENED)
