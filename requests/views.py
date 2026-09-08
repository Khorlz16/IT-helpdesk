from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.contrib import messages
from django.views.decorators.http import require_POST
from django.utils import timezone
from django.db import models
from django.forms import formset_factory
from django.db.models import Avg, Count, ExpressionWrapper, F, FloatField, Sum, Value
from django.db.models.functions import Extract
from .models import Request, Category, Notification, RequestItem
from accounts.models import User, Department, Branch
from .forms import RequestForm, RequestItemForm
from .services import RequestService

RequestItemFormSet = formset_factory(RequestItemForm, extra=1, can_delete=True)

@login_required
def dashboard(request):
    user = request.user
    if user.is_it_admin:
        qs = Request.objects.select_related('requester', 'assigned_to', 'category')
        if not user.is_central_admin:
            qs = qs.filter(branch=user.branch)
        total = qs.count()
        pending = qs.filter(status=Request.Status.PENDING).count()
        approved = qs.filter(status=Request.Status.APPROVED).count()
        assigned = qs.filter(status=Request.Status.ASSIGNED).count()
        in_progress = qs.filter(status=Request.Status.IN_PROGRESS).count()
        completed = qs.filter(status=Request.Status.COMPLETED).count()
        closed = qs.filter(status=Request.Status.CLOSED).count()
        rejected = qs.filter(status=Request.Status.REJECTED).count()
        recent = qs.order_by('-created_at')[:10]
        context = {
            'total': total,
            'pending': pending,
            'approved': approved,
            'assigned': assigned,
            'in_progress': in_progress,
            'completed': completed,
            'closed': closed,
            'rejected': rejected,
            'recent': recent,
        }
        template = 'requests/admin_dashboard.html'
    elif user.is_it_staff:
        qs = Request.objects.select_related('requester', 'category').filter(assigned_to=user)
        if not user.is_central_admin:
            qs = qs.filter(branch=user.branch)
        assigned_requests = qs.exclude(status__in=[Request.Status.CLOSED, Request.Status.REJECTED]).order_by('-created_at')
        in_progress_count = qs.filter(status=Request.Status.IN_PROGRESS).count()
        completed_count = qs.filter(status=Request.Status.COMPLETED).count()
        total_assigned_count = assigned_requests.count()
        context = {
            'assigned_requests': assigned_requests,
            'in_progress_count': in_progress_count,
            'completed_count': completed_count,
            'total_assigned_count': total_assigned_count,
        }
        template = 'requests/staff_dashboard.html'
    else:
        my_requests = Request.objects.select_related('category').filter(requester=user).order_by('-created_at')[:10]
        total = Request.objects.filter(requester=user).count()
        context = {
            'my_requests': my_requests,
            'total': total,
        }
        template = 'requests/employee_dashboard.html'
    return render(request, template, context)

@login_required
def create_request(request):
    if request.method == 'POST':
        form = RequestForm(request.POST)
        item_formset = RequestItemFormSet(request.POST, prefix='items')
        if form.is_valid() and item_formset.is_valid():
            category = form.cleaned_data['category']
            description = form.cleaned_data['description']
            requested_priority = form.cleaned_data['requested_priority']
            req = RequestService.submit_request(
                employee=request.user,
                category=category,
                description=description,
                requested_priority=requested_priority,
            )
            for item_form in item_formset:
                if item_form.cleaned_data and not item_form.cleaned_data.get('DELETE', False):
                    item = item_form.save(commit=False)
                    item.request = req
                    item.save()
            return redirect('requests:request_detail', pk=req.pk)
    else:
        form = RequestForm()
        item_formset = RequestItemFormSet(prefix='items')
    return render(request, 'requests/create_request.html', {
        'form': form,
        'item_formset': item_formset,
    })

@login_required
def request_list(request):
    user = request.user
    qs = Request.objects.select_related('requester', 'assigned_to', 'category').order_by('-created_at')
    if user.is_it_staff:
        qs = qs.filter(assigned_to=user, branch=user.branch)
    elif user.is_it_admin:
        if not user.is_central_admin:
            qs = qs.filter(branch=user.branch)
    else:
        qs = qs.filter(requester=user)

    q = request.GET.get('q', '').strip()
    if q:
        qs = qs.filter(
            models.Q(description__icontains=q) |
            models.Q(requester__username__icontains=q) |
            models.Q(requester__first_name__icontains=q) |
            models.Q(requester__last_name__icontains=q)
        )
    status = request.GET.get('status', '')
    if status:
        qs = qs.filter(status=status)
    category_id = request.GET.get('category', '')
    if category_id:
        qs = qs.filter(category_id=category_id)
    priority = request.GET.get('priority', '')
    if priority:
        qs = qs.filter(priority=priority)
    date_from = request.GET.get('date_from', '')
    if date_from:
        qs = qs.filter(created_at__date__gte=date_from)
    date_to = request.GET.get('date_to', '')
    if date_to:
        qs = qs.filter(created_at__date__lte=date_to)

    categories = Category.objects.all()
    statuses = Request.Status.choices
    priorities = Request.Priority.choices

    context = {
        'requests': qs,
        'categories': categories,
        'statuses': statuses,
        'priorities': priorities,
        'selected_status': status,
        'selected_category': category_id,
        'selected_priority': priority,
        'q': q,
        'date_from': date_from,
        'date_to': date_to,
    }
    return render(request, 'requests/request_list.html', context)

@login_required
def request_detail(request, pk):
    req = get_object_or_404(
        Request.objects.select_related('requester', 'assigned_to', 'category').prefetch_related(
            'items',
            'updates__user',
            'history__actor',
            'notifications',
        ),
        pk=pk,
    )
    if request.user.is_it_admin:
        if not request.user.is_central_admin and request.user.branch != req.branch:
            raise PermissionDenied('You can only view requests in your branch.')
    elif request.user != req.requester and request.user != req.assigned_to:
        raise PermissionDenied('You do not have permission to view this request.')
    can_reopen = False
    if request.user == req.requester and req.status == Request.Status.CLOSED and req.closed_at:
        if not (request.user.is_it_admin and req.requester == request.user):
            if (timezone.now() - req.closed_at).total_seconds() <= 72*3600:
                can_reopen = True
    context = {
        'req': req,
        'is_admin': request.user.is_it_admin,
        'is_staff': request.user.is_it_staff,
        'is_employee': request.user.is_employee,
        'staff_list': User.objects.filter(role=User.Role.IT_STAFF, is_active=True, branch=req.branch) if request.user.is_it_admin else None,
        'can_reopen': can_reopen,
    }
    return render(request, 'requests/request_detail.html', context)

@login_required
@require_POST
def request_action(request, pk):
    req = get_object_or_404(Request, pk=pk)
    action = request.POST.get('action')
    user = request.user

    if user.is_it_admin and req.requester == user:
        messages.error(request, 'Super admins cannot process their own tickets. Please ask another super admin to handle it.')
        return redirect('requests:request_detail', pk=pk)

    try:
        if action == 'approve':
            RequestService.approve_request(user, req)
        elif action == 'reject':
            reason = request.POST.get('reason', '')
            RequestService.reject_request(user, req, reason)
        elif action == 'assign':
            staff_id = request.POST.get('staff_id')
            staff = User.objects.get(pk=staff_id) if staff_id else None
            if not staff:
                raise ValueError('Please select a staff member.')
            if req.status == Request.Status.REOPENED:
                RequestService.reassign_request(user, req, staff)
            else:
                RequestService.assign_request(user, req, staff)
        elif action == 'start':
            RequestService.start_work(user, req)
        elif action == 'complete':
            resolution = request.POST.get('resolution', '')
            RequestService.complete_work(user, req, resolution)
        elif action == 'close':
            RequestService.close_request(user, req)
        elif action == 'escalate':
            reason = request.POST.get('reason', '')
            RequestService.escalate(user, req, reason)
        elif action == 'comment':
            message = request.POST.get('message', '')
            RequestService.add_update(user, req, message)
        elif action == 'reopen_request':
            reason = request.POST.get('reason', '')
            RequestService.request_reopen(user, req, reason)
        elif action == 'approve_reopen':
            RequestService.approve_reopen(user, req)
        elif action == 'reject_reopen':
            reason = request.POST.get('reason', '')
            RequestService.reject_reopen(user, req, reason)
        elif action == 'change_priority':
            new_priority = request.POST.get('priority')
            if new_priority not in [p[0] for p in Request.Priority.choices]:
                raise ValueError('Invalid priority value.')
            RequestService.change_priority(user, req, new_priority)
        else:
            messages.error(request, 'Invalid action.')
    except (PermissionDenied, ValueError) as e:
        messages.error(request, str(e))
    return redirect('requests:request_detail', pk=pk)

@login_required
def notification_list(request):
    notifications = request.user.notifications.select_related('request').all().order_by('-created_at')
    return render(request, 'requests/notification_list.html', {'notifications': notifications})

@login_required
@require_POST
def mark_all_notifications_read(request):
    request.user.notifications.filter(is_read=False).update(is_read=True)
    request.session['toast_shown'] = True
    request.session['show_notification_after_login'] = False
    request.session.pop('notification_toast_seen', None)
    return redirect('requests:notification_list')

@login_required
def mark_notification_read(request, pk):
    notification = get_object_or_404(Notification, pk=pk, recipient=request.user)
    notification.is_read = True
    notification.save()
    request.session['notification_toast_seen'] = str(notification.pk)
    request.session['toast_shown'] = True
    request.session['show_notification_after_login'] = False
    return redirect('requests:request_detail', pk=notification.request.pk)

@login_required
def statistics(request):
    if not request.user.is_it_admin:
        raise PermissionDenied('Only IT Admin can view statistics.')
    qs = Request.objects.all()
    if not request.user.is_central_admin:
        qs = qs.filter(branch=request.user.branch)
    # Status counts with labels
    status_counts = qs.values('status').annotate(count=Count('id')).order_by('status')
    status_labels = dict(Request.Status.choices)
    for row in status_counts:
        row['status_display'] = status_labels.get(row['status'], row['status'])
    # Priority counts with labels
    priority_counts = qs.values('priority').annotate(count=Count('id')).order_by('priority')
    priority_labels = dict(Request.Priority.choices)
    for row in priority_counts:
        row['priority_display'] = priority_labels.get(row['priority'], row['priority'])
    # Category counts
    category_counts = qs.values('category__name').annotate(count=Count('id')).order_by('-count')
    # Equipment items summary
    equipment_summary = RequestItem.objects.filter(request__in=qs).values('item_name').annotate(
        total_quantity=Sum('quantity'),
        request_count=Count('request', distinct=True)
    ).order_by('-total_quantity')
    # Branch and department counts
    branch_counts = qs.values('requester__branch__name').annotate(count=Count('id')).order_by('-count')
    department_counts = qs.values('requester__department__name').annotate(count=Count('id')).order_by('-count')
    # IT Staff workload
    it_staff_qs = User.objects.filter(role=User.Role.IT_STAFF)
    if not request.user.is_central_admin:
        it_staff_qs = it_staff_qs.filter(branch=request.user.branch)
    it_staff_workload = it_staff_qs.annotate(
        assigned_count=Count('requests_assigned'),
        in_progress_count=Count('requests_assigned', filter=models.Q(requests_assigned__status=Request.Status.IN_PROGRESS)),
        completed_count=Count('requests_assigned', filter=models.Q(requests_assigned__status=Request.Status.COMPLETED)),
    ).order_by('-assigned_count')
    # Safe cross-database aggregation for average resolution time.
    resolution_rows = qs.filter(closed_at__isnull=False, created_at__isnull=False).values_list('created_at', 'closed_at')
    resolution_hours = []
    for started, ended in resolution_rows:
        if started and ended:
            delta = ended - started
            seconds = delta.total_seconds()
            if seconds > 0:
                resolution_hours.append(seconds / 3600)
    avg_resolution_hours = sum(resolution_hours) / len(resolution_hours) if resolution_hours else 0

    # Advanced ORM aggregation for average items attached per request.
    avg_items_per_request = qs.annotate(item_count=Count('items')).aggregate(avg_items=Avg('item_count'))['avg_items'] or 0

    context = {
        'status_counts': status_counts,
        'category_counts': category_counts,
        'priority_counts': priority_counts,
        'equipment_summary': equipment_summary,
        'branch_counts': branch_counts,
        'department_counts': department_counts,
        'it_staff_workload': it_staff_workload,
        'avg_resolution_hours': avg_resolution_hours,
        'avg_items_per_request': avg_items_per_request,
    }
    return render(request, 'requests/statistics.html', context)

from django.http import JsonResponse

@login_required
@require_POST
def mark_notification_read_ajax(request, pk):
    notification = get_object_or_404(Notification, pk=pk, recipient=request.user)
    notification.is_read = True
    notification.save()
    request.session['notification_toast_seen'] = str(notification.pk)
    request.session['toast_shown'] = True
    request.session['show_notification_after_login'] = False
    return JsonResponse({'status': 'ok'})
