from django.db import models
from django.conf import settings
from django.utils import timezone

class Category(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)

    def __str__(self):
        return self.name

class Request(models.Model):
    class Status(models.TextChoices):
        PENDING = 'PENDING', 'Pending'
        APPROVED = 'APPROVED', 'Approved'
        ASSIGNED = 'ASSIGNED', 'Assigned'
        IN_PROGRESS = 'IN_PROGRESS', 'In Progress'
        COMPLETED = 'COMPLETED', 'Completed'
        CLOSED = 'CLOSED', 'Closed'
        REJECTED = 'REJECTED', 'Rejected'
        REOPEN_REQUESTED = 'REOPEN_REQUESTED', 'Reopen Requested'
        REOPENED = 'REOPENED', 'Reopened'
        REASSIGNED = 'REASSIGNED', 'Reassigned'

    class Priority(models.TextChoices):
        LOW = 'LOW', 'Low'
        NORMAL = 'NORMAL', 'Normal'
        HIGH = 'HIGH', 'High'
        URGENT = 'URGENT', 'Urgent'

    branch = models.ForeignKey(
        'accounts.Branch',
        on_delete=models.PROTECT,
        related_name='requests',
        null=False,
        blank=False,
        db_index=True,
    )
    requester = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='requests_submitted',
        db_index=True,
    )
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='requests_assigned',
        db_index=True,
    )
    category = models.ForeignKey(
        Category,
        on_delete=models.PROTECT,
        related_name='requests',
        db_index=True,
    )
    description = models.TextField()
    requested_priority = models.CharField(
        max_length=10,
        choices=Priority.choices,
        default=Priority.NORMAL,
    )
    priority = models.CharField(
        max_length=10,
        choices=Priority.choices,
        default=Priority.NORMAL,
        db_index=True,
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
        db_index=True,
    )
    request_number = models.CharField(max_length=20, unique=True, blank=True, null=True, db_index=True)
    rejection_reason = models.TextField(blank=True, null=True)
    resolution = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True, db_index=True)
    closed_at = models.DateTimeField(blank=True, null=True, db_index=True)

    def generate_request_number(self):
        if self.branch_id is None:
            raise ValueError('Request branch is required before generating a request number.')
        if self.request_number:
            return self.request_number
        branch_code = self.branch.code.upper()
        year = timezone.now().strftime('%Y')
        prefix = f'REQ-{branch_code}-{year}-'
        last_request = Request.objects.filter(request_number__startswith=prefix).order_by('-request_number').first()
        seq = 1 if not last_request else int(last_request.request_number.split('-')[-1]) + 1
        candidate = f'{prefix}{seq:03d}'
        while Request.objects.filter(request_number=candidate).exists():
            seq += 1
            candidate = f'{prefix}{seq:03d}'
        self.request_number = candidate
        return candidate

    def save(self, *args, **kwargs):
        if not self.request_number and self.branch_id:
            self.generate_request_number()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.request_number or f'REQ-{self.pk}'} - {self.category.name} ({self.get_status_display()})"

class RequestItem(models.Model):
    request = models.ForeignKey(
        Request,
        on_delete=models.CASCADE,
        related_name='items'
    )
    item_name = models.CharField(max_length=200)
    quantity = models.PositiveIntegerField(default=1)

    def __str__(self):
        return f"{self.item_name} x{self.quantity}"

class RequestUpdate(models.Model):
    request = models.ForeignKey(
        Request,
        on_delete=models.CASCADE,
        related_name='updates',
        db_index=True,
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='request_updates',
        db_index=True,
    )
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Update by {self.user.username} on REQ-{self.request.id}"

class RequestHistory(models.Model):
    request = models.ForeignKey(
        Request,
        on_delete=models.CASCADE,
        related_name='history'
    )
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='request_history_actions'
    )
    action = models.CharField(max_length=100)
    old_value = models.TextField(blank=True, null=True)
    new_value = models.TextField(blank=True, null=True)
    reason = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.action} by {self.actor.username} at {self.created_at}"

class Escalation(models.Model):
    request = models.ForeignKey(
        Request,
        on_delete=models.CASCADE,
        related_name='escalations'
    )
    escalated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='escalations_made'
    )
    reason = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Escalation for REQ-{self.request.id} by {self.escalated_by.username}"

class Notification(models.Model):
    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='notifications',
        db_index=True,
    )
    request = models.ForeignKey(
        Request,
        on_delete=models.CASCADE,
        related_name='notifications',
        db_index=True,
    )
    message = models.CharField(max_length=255)
    is_read = models.BooleanField(default=False, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    def __str__(self):
        return f"Notification for {self.recipient.username}: {self.message}"
