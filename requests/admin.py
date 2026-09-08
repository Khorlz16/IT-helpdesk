from django.contrib import admin
from .models import (
    Category, Request, RequestItem, RequestUpdate,
    RequestHistory, Escalation, Notification
)

class RequestItemInline(admin.TabularInline):
    model = RequestItem
    extra = 1

class RequestUpdateInline(admin.TabularInline):
    model = RequestUpdate
    extra = 1

class RequestHistoryInline(admin.TabularInline):
    model = RequestHistory
    extra = 0
    can_delete = False
    readonly_fields = ['actor', 'action', 'old_value', 'new_value', 'reason', 'created_at']

class EscalationInline(admin.TabularInline):
    model = Escalation
    extra = 0

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'description']

@admin.register(Request)
class RequestAdmin(admin.ModelAdmin):
    list_display = ['id', 'requester', 'category', 'status', 'priority', 'assigned_to', 'created_at']
    list_filter = ['status', 'priority', 'category', 'assigned_to']
    search_fields = ['requester__username', 'description']
    inlines = [RequestItemInline, RequestUpdateInline, RequestHistoryInline, EscalationInline]

@admin.register(RequestItem)
class RequestItemAdmin(admin.ModelAdmin):
    list_display = ['request', 'item_name', 'quantity']

@admin.register(RequestUpdate)
class RequestUpdateAdmin(admin.ModelAdmin):
    list_display = ['request', 'user', 'created_at']

@admin.register(RequestHistory)
class RequestHistoryAdmin(admin.ModelAdmin):
    list_display = ['request', 'actor', 'action', 'created_at']

@admin.register(Escalation)
class EscalationAdmin(admin.ModelAdmin):
    list_display = ['request', 'escalated_by', 'created_at']

@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ['recipient', 'request', 'message', 'is_read', 'created_at']
