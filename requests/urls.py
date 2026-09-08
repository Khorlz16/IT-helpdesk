from django.urls import path
from . import views

app_name = 'requests'

urlpatterns = [
    path('dashboard/', views.dashboard, name='dashboard'),
    path('create/', views.create_request, name='create_request'),
    path('list/', views.request_list, name='request_list'),
    path('notifications/', views.notification_list, name='notification_list'),
    path('notifications/mark-all-read/', views.mark_all_notifications_read, name='mark_all_notifications_read'),
    path('notifications/<int:pk>/read/', views.mark_notification_read, name='mark_notification_read'),
    path('notifications/<int:pk>/mark-read-ajax/', views.mark_notification_read_ajax, name='mark_notification_read_ajax'),
    path('statistics/', views.statistics, name='statistics'),
    path('<int:pk>/', views.request_detail, name='request_detail'),
    path('<int:pk>/action/', views.request_action, name='request_action'),
]
