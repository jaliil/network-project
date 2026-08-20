from django.urls import path
from . import views

urlpatterns = [
    path('', views.dashboard_view, name='dashboard'),
    path('add-device/', views.add_device_view, name='add_device'),
    path('bulk-upload/', views.bulk_upload_view, name='bulk_upload'),
    path('export-devices/', views.export_devices_view, name='export_devices'),
    path('device-list/', views.device_list, name='device_list'),
    path('search-mac/', views.search_mac_view, name='search_mac'),
    path('check-signal/', views.check_signal_view, name='check_signal'),
    path('wireless-clients/', views.wireless_clients_view, name='wireless_clients'),
    path('run-mikrotik/', views.run_mikrotik_view, name='run_mikrotik'),
    path('run-cisco/', views.run_cisco_view, name='run_cisco'),
    path('switch-report/', views.switch_report_view, name='switch_report'),
    path('approve-command/<int:history_id>/', views.approve_command_view, name='approve_command'),
    path('reject-command/<int:history_id>/', views.reject_command_view, name='reject_command'),
    path('connect/', views.employee_panel_view, name='employee_panel'),
    path('profile/', views.update_profile, name='update_profile'),
    path('ping-log/', views.smart_ping_and_log, name='smart_ping_and_log'),
    path('map/', views.live_map_view, name='live_map'),
    path('map-management/', views.map_management_view, name='map_management'),
    path('map-management/fetch-interfaces/', views.fetch_interfaces_view, name='fetch_interfaces'),
]