from django.db import transaction
from django.utils import timezone
from datetime import timedelta
from django.core.exceptions import PermissionDenied
from accounts.models import User
from .models import (
    Request, RequestHistory, Notification, Escalation,
    RequestUpdate, RequestItem
)

class RequestService:
    @staticmethod
    def _ensure_admin_not_self_processing(admin, request):
        if admin.is_it_admin and request.requester == admin:
            raise PermissionDenied('Super admins cannot process their own requests. Please ask another super admin.')

    @staticmethod
    def _ensure_branch_access(admin, request):
        if not admin.is_central_admin and admin.branch != request.branch:
            raise PermissionDenied('You can only manage requests in your branch.')

    @staticmethod
    def generate_request_number(branch):
        if branch is None:
            raise ValueError('Branch is required to generate a request number.')
        year = timezone.now().year
        prefix = f'REQ-{branch.code}-{year}-'
        last_request = Request.objects.filter(request_number__startswith=prefix).order_by('-request_number').first()
        seq = 1 if not last_request else int(last_request.request_number.split('-')[-1]) + 1
        return f'{prefix}{seq:03d}'

    @staticmethod
    @transaction.atomic
    def submit_request(employee, category, description, requested_priority, items=None):
        if employee.is_anonymous:
            raise PermissionDenied('A valid user is required to submit a request.')
        request = Request.objects.create(
            requester=employee,
            branch=employee.branch,
            category=category,
            description=description,
            requested_priority=requested_priority,
            priority=requested_priority,
            status=Request.Status.PENDING,
        )
        request.request_number = RequestService.generate_request_number(employee.branch)
        request.save(update_fields=['request_number'])
        if items:
            for item in items:
                RequestItem.objects.create(
                    request=request,
                    item_name=item['item_name'],
                    quantity=item.get('quantity', 1)
                )
        RequestHistory.objects.create(
            request=request,
            actor=employee,
            action='SUBMITTED',
            new_value='Request submitted'
        )
        admins = User.objects.filter(role=User.Role.IT_ADMIN, is_active=True)
        if not employee.is_central_admin and employee.branch:
            admins = admins.filter(branch=employee.branch)
        request_code = request.request_number or f'REQ-{request.id}'
        for admin in admins:
            Notification.objects.create(
                recipient=admin,
                request=request,
                message=f'New request {request_code} submitted by {employee.get_full_name()}'
            )
        return request

    @staticmethod
    @transaction.atomic
    def approve_request(admin, request):
        if not admin.is_it_admin:
            raise PermissionDenied('Only IT Admin can approve requests.')
        RequestService._ensure_admin_not_self_processing(admin, request)
        RequestService._ensure_branch_access(admin, request)
        if request.status != Request.Status.PENDING:
            raise ValueError('Only pending requests can be approved.')
        request.status = Request.Status.APPROVED
        request.save()
        RequestHistory.objects.create(
            request=request,
            actor=admin,
            action='APPROVED',
            old_value=Request.Status.PENDING,
            new_value=Request.Status.APPROVED
        )
        Notification.objects.create(
            recipient=request.requester,
            request=request,
            message=f'Your request {request.request_number or f"REQ-{request.id}"} has been approved.'
        )

    @staticmethod
    @transaction.atomic
    def reject_request(admin, request, reason):
        if not admin.is_it_admin:
            raise PermissionDenied('Only IT Admin can reject requests.')
        RequestService._ensure_admin_not_self_processing(admin, request)
        RequestService._ensure_branch_access(admin, request)
        if request.status != Request.Status.PENDING:
            raise ValueError('Only pending requests can be rejected.')
        request.status = Request.Status.REJECTED
        request.rejection_reason = reason
        request.save()
        RequestHistory.objects.create(
            request=request,
            actor=admin,
            action='REJECTED',
            old_value=Request.Status.PENDING,
            new_value=Request.Status.REJECTED,
            reason=reason
        )
        Notification.objects.create(
            recipient=request.requester,
            request=request,
            message=f'Your request {request.request_number or f"REQ-{request.id}"} was rejected. Reason: {reason}'
        )

    @staticmethod
    @transaction.atomic
    def assign_request(admin, request, staff):
        if not admin.is_it_admin:
            raise PermissionDenied('Only IT Admin can assign requests.')
        RequestService._ensure_admin_not_self_processing(admin, request)
        RequestService._ensure_branch_access(admin, request)
        if request.status not in [Request.Status.APPROVED, Request.Status.REOPENED]:
            raise ValueError('Only approved or reopened requests can be assigned.')
        if not staff.is_it_staff:
            raise ValueError('Assignee must be IT Staff.')
        if staff.branch != request.branch:
            raise PermissionDenied('Staff must be in the same branch as the request.')
        old_assignee = request.assigned_to
        request.assigned_to = staff
        request.status = Request.Status.ASSIGNED
        request.save()
        RequestHistory.objects.create(
            request=request,
            actor=admin,
            action='ASSIGNED',
            old_value=str(old_assignee) if old_assignee else 'Unassigned',
            new_value=str(staff)
        )
        Notification.objects.create(
            recipient=staff,
            request=request,
            message=f'You have been assigned {request.request_number or f"REQ-{request.id}"}.'
        )
        Notification.objects.create(
            recipient=request.requester,
            request=request,
            message=f'Your request {request.request_number or f"REQ-{request.id}"} has been assigned to {staff.get_full_name()}.'
        )

    @staticmethod
    @transaction.atomic
    def reassign_request(admin, request, staff):
        if not admin.is_it_admin:
            raise PermissionDenied('Only IT Admin can reassign requests.')
        RequestService._ensure_admin_not_self_processing(admin, request)
        RequestService._ensure_branch_access(admin, request)
        if request.status not in [Request.Status.REOPENED, Request.Status.REASSIGNED]:
            raise ValueError('Only reopened or reassigned requests can be reassigned.')
        if not staff.is_it_staff:
            raise ValueError('Assignee must be IT Staff.')
        if staff.branch != request.branch:
            raise PermissionDenied('Staff must be in the same branch as the request.')
        old_assignee = request.assigned_to
        request.assigned_to = staff
        request.status = Request.Status.REASSIGNED
        request.save()
        RequestHistory.objects.create(
            request=request,
            actor=admin,
            action='REASSIGNED',
            old_value=str(old_assignee) if old_assignee else 'Unassigned',
            new_value=str(staff)
        )
        Notification.objects.create(
            recipient=staff,
            request=request,
            message=f'You have been reassigned {request.request_number or f"REQ-{request.id}"}.'
        )
        Notification.objects.create(
            recipient=request.requester,
            request=request,
            message=f'Your request {request.request_number or f"REQ-{request.id}"} has been reassigned to {staff.get_full_name()}.'
        )

    @staticmethod
    @transaction.atomic
    def start_work(staff, request):
        if not staff.is_it_staff:
            raise PermissionDenied('Only IT Staff can start work.')
        if request.assigned_to != staff:
            raise PermissionDenied('You can only start work on requests assigned to you.')
        if request.status not in [Request.Status.ASSIGNED, Request.Status.REASSIGNED]:
            raise ValueError('Only assigned or reassigned requests can be started.')
        request.status = Request.Status.IN_PROGRESS
        request.save()
        RequestHistory.objects.create(
            request=request,
            actor=staff,
            action='IN_PROGRESS',
            old_value=Request.Status.ASSIGNED,
            new_value=Request.Status.IN_PROGRESS
        )
        Notification.objects.create(
            recipient=request.requester,
            request=request,
            message=f'Work started on your request {request.request_number or f"REQ-{request.id}"}.'
        )

    @staticmethod
    @transaction.atomic
    def complete_work(staff, request, resolution):
        if not staff.is_it_staff:
            raise PermissionDenied('Only IT Staff can complete work.')
        if request.assigned_to != staff:
            raise PermissionDenied('You can only complete requests assigned to you.')
        if request.status != Request.Status.IN_PROGRESS:
            raise ValueError('Only in-progress requests can be completed.')
        request.status = Request.Status.COMPLETED
        request.resolution = resolution
        request.save()
        RequestHistory.objects.create(
            request=request,
            actor=staff,
            action='COMPLETED',
            old_value=Request.Status.IN_PROGRESS,
            new_value=Request.Status.COMPLETED,
            reason=resolution
        )
        admins = User.objects.filter(role=User.Role.IT_ADMIN, is_active=True)
        if not staff.is_central_admin and request.branch:
            admins = admins.filter(branch=request.branch)
        for admin in admins:
            Notification.objects.create(
                recipient=admin,
                request=request,
                message=f'{request.request_number or f"REQ-{request.id}"} completed by {staff.get_full_name()}.'
            )

    @staticmethod
    @transaction.atomic
    def close_request(admin, request):
        if not admin.is_it_admin:
            raise PermissionDenied('Only IT Admin can close requests.')
        RequestService._ensure_admin_not_self_processing(admin, request)
        RequestService._ensure_branch_access(admin, request)
        if request.status != Request.Status.COMPLETED:
            raise ValueError('Only completed requests can be closed.')
        request.status = Request.Status.CLOSED
        request.closed_at = timezone.now()
        request.save()
        RequestHistory.objects.create(
            request=request,
            actor=admin,
            action='CLOSED',
            old_value=Request.Status.COMPLETED,
            new_value=Request.Status.CLOSED
        )
        Notification.objects.create(
            recipient=request.requester,
            request=request,
            message=f'Your request {request.request_number or f"REQ-{request.id}"} has been closed.'
        )

    @staticmethod
    @transaction.atomic
    def add_update(user, request, message):
        if user != request.requester and user != request.assigned_to and not user.is_it_admin:
            raise PermissionDenied('You cannot comment on this request.')
        RequestUpdate.objects.create(
            request=request,
            user=user,
            message=message
        )
        recipients = set()
        if user == request.requester:
            recipients.add(request.assigned_to)
            admins = User.objects.filter(role=User.Role.IT_ADMIN, is_active=True)
            if not user.is_central_admin and request.branch:
                admins = admins.filter(branch=request.branch)
            recipients.update(admins)
        else:
            recipients.add(request.requester)
        recipients.discard(user)
        recipients = [r for r in recipients if r is not None]
        for r in recipients:
            Notification.objects.create(
                recipient=r,
                request=request,
                message=f'New comment on {request.request_number or f"REQ-{request.id}"} by {user.get_full_name()}.'
            )

    @staticmethod
    @transaction.atomic
    def escalate(staff, request, reason):
        if not staff.is_it_staff:
            raise PermissionDenied('Only IT Staff can escalate.')
        if request.assigned_to != staff:
            raise PermissionDenied('You can only escalate requests assigned to you.')
        if request.status not in [Request.Status.ASSIGNED, Request.Status.REASSIGNED, Request.Status.IN_PROGRESS]:
            raise ValueError('Only assigned, reassigned or in-progress requests can be escalated.')
        Escalation.objects.create(
            request=request,
            escalated_by=staff,
            reason=reason
        )
        RequestHistory.objects.create(
            request=request,
            actor=staff,
            action='ESCALATED',
            reason=reason
        )
        admins = User.objects.filter(role=User.Role.IT_ADMIN, is_active=True)
        if not staff.is_central_admin and request.branch:
            admins = admins.filter(branch=request.branch)
        for admin in admins:
            Notification.objects.create(
                recipient=admin,
                request=request,
                message=f'{request.request_number or f"REQ-{request.id}"} escalated by {staff.get_full_name()}.'
            )

    @staticmethod
    @transaction.atomic
    def request_reopen(employee, request, reason):
        if not employee.is_employee:
            raise PermissionDenied('Only employees can request reopening.')
        if employee != request.requester:
            raise PermissionDenied('You can only reopen your own requests.')
        if request.status != Request.Status.CLOSED:
            raise ValueError('Only closed requests can be reopened.')
        if request.closed_at and (timezone.now() - request.closed_at) > timedelta(hours=72):
            raise ValueError('Reopen request must be made within 72 hours of closure.')
        request.status = Request.Status.REOPEN_REQUESTED
        request.save()
        RequestHistory.objects.create(
            request=request,
            actor=employee,
            action='REOPEN_REQUESTED',
            reason=reason
        )
        admins = User.objects.filter(role=User.Role.IT_ADMIN, is_active=True)
        if not employee.is_central_admin and request.branch:
            admins = admins.filter(branch=request.branch)
        for admin in admins:
            Notification.objects.create(
                recipient=admin,
                request=request,
                message=f'{request.request_number or f"REQ-{request.id}"} reopen requested by {employee.get_full_name()}.'
            )

    @staticmethod
    @transaction.atomic
    def approve_reopen(admin, request):
        if not admin.is_it_admin:
            raise PermissionDenied('Only IT Admin can approve reopen requests.')
        RequestService._ensure_admin_not_self_processing(admin, request)
        RequestService._ensure_branch_access(admin, request)
        if request.status != Request.Status.REOPEN_REQUESTED:
            raise ValueError('Only reopen-requested requests can be approved.')
        request.status = Request.Status.REOPENED
        request.closed_at = None
        request.save()
        RequestHistory.objects.create(
            request=request,
            actor=admin,
            action='REOPEN_APPROVED',
            old_value=Request.Status.REOPEN_REQUESTED,
            new_value=Request.Status.REOPENED
        )
        Notification.objects.create(
            recipient=request.requester,
            request=request,
            message=f'Your reopen request for {request.request_number or f"REQ-{request.id}"} has been approved.'
        )

    @staticmethod
    @transaction.atomic
    def reject_reopen(admin, request, reason):
        if not admin.is_it_admin:
            raise PermissionDenied('Only IT Admin can reject reopen requests.')
        RequestService._ensure_admin_not_self_processing(admin, request)
        RequestService._ensure_branch_access(admin, request)
        if request.status != Request.Status.REOPEN_REQUESTED:
            raise ValueError('Only reopen-requested requests can be rejected.')
        request.status = Request.Status.CLOSED
        request.rejection_reason = reason
        request.save()
        RequestHistory.objects.create(
            request=request,
            actor=admin,
            action='REOPEN_REJECTED',
            old_value=Request.Status.REOPEN_REQUESTED,
            new_value=Request.Status.CLOSED,
            reason=reason
        )
        Notification.objects.create(
            recipient=request.requester,
            request=request,
            message=f'Your reopen request for {request.request_number or f"REQ-{request.id}"} was rejected. Reason: {reason}'
        )

    @staticmethod
    @transaction.atomic
    def change_priority(admin, request, new_priority):
        if not admin.is_it_admin:
            raise PermissionDenied('Only IT Admin can change priority.')
        RequestService._ensure_admin_not_self_processing(admin, request)
        RequestService._ensure_branch_access(admin, request)
        old_priority = request.priority
        if old_priority == new_priority:
            return
        request.priority = new_priority
        request.save()
        RequestHistory.objects.create(
            request=request,
            actor=admin,
            action='PRIORITY_CHANGED',
            old_value=old_priority,
            new_value=new_priority
        )
        notification_code = request.request_number or f'REQ-{request.id}'
        Notification.objects.create(
            recipient=request.requester,
            request=request,
            message=f'Priority of {notification_code} changed from {old_priority} to {new_priority} by admin.'
        )
        if request.assigned_to:
            Notification.objects.create(
                recipient=request.assigned_to,
                request=request,
                message=f'Priority of {notification_code} changed from {old_priority} to {new_priority}.'
            )
