from django.urls import path
from django.contrib.auth.views import LogoutView
from . import views

urlpatterns = [
    # Auth & Dashboard
    path('login/', views.CustomLoginView.as_view(), name='login'),
    path('logout/', LogoutView.as_view(next_page='login'), name='logout'),
    path('', views.dashboard_view, name='dashboard'),

    # Device Management
    path('add-device/', views.add_device_view, name='add_device'),
    path('devices/', views.device_list, name='device_list'),
    path('bulk-upload/', views.bulk_upload_view, name='bulk_upload'),
    path('export-devices/', views.export_devices_view, name='export_devices'),

    # Network Operations (Run Config)
    path('run-mikrotik/', views.run_mikrotik_view, name='run_mikrotik'),
    path('run-cisco/', views.run_cisco_view, name='run_cisco'),
    path('approve/<int:history_id>/', views.approve_command_view, name='approve_command'),
    path('reject/<int:history_id>/', views.reject_command_view, name='reject_command'),

    # Network Tools & Reports
    path('search-mac/', views.search_mac_view, name='search_mac'),
    path('check-signal/', views.check_signal_view, name='check_signal'),
    path('wireless-clients/', views.wireless_clients_view, name='wireless_clients'),
    path('switch-report/', views.switch_report_view, name='switch_report'),
    path('smart-ping/', views.smart_ping_and_log, name='smart_ping_and_log'),

    # Employee Panel
    path('employee-panel/', views.employee_panel_view, name='employee_panel'),
    path('update-profile/', views.update_profile, name='update_profile'),

    # Map & Topology Management
    path('map-management/', views.map_management_view, name='map_management'),
    path('map-management/fetch-interfaces/', views.fetch_interfaces_view, name='fetch_interfaces'),
    
    # Live Map & APIs
    path('live-map/', views.live_map_view, name='live_map'),
    path('api/live-map-data/', views.live_map_data_api, name='live_map_data_api'), 

    # ==========================================
    # Smart Log Analyzer
    # ==========================================
    path('smart-log-analyzer/', views.device_logs_analyzer_view, name='device_logs_analyzer'),
    path('api/fetch-device-logs/', views.fetch_device_logs_api, name='fetch_device_logs'),
    path('api/ai-analyze-log/', views.analyze_log_ai_api, name='analyze_log_ai_api'),
    path('customer-configs/', views.customer_configs_view, name='customer_configs'),
]