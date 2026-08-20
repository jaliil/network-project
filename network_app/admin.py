from django.contrib import admin
from .models import Province, BTS, Device, ConfigCommand, ActivityLog, Profile, CommandHistory, UserProvinceCredential, NetworkLink

@admin.register(Province)
class ProvinceAdmin(admin.ModelAdmin):
    list_display = ('name', 'mt_user', 'cisco_user', 'mt_port', 'cisco_port')

@admin.register(BTS)
class BTSAdmin(admin.ModelAdmin):
    list_display = ('name', 'province', 'latitude', 'longitude')
    list_filter = ('province',)
    search_fields = ('name',)

@admin.register(Device)
class DeviceAdmin(admin.ModelAdmin):
    list_display = ('ip_address', 'device_type', 'bts', 'mac_address')
    list_filter = ('device_type', 'bts__province', 'bts')
    search_fields = ('ip_address', 'mac_address', 'name')

@admin.register(ConfigCommand)
class ConfigCommandAdmin(admin.ModelAdmin):
    list_display = ('command_order', 'device_type', 'command_text', 'is_active')
    list_filter = ('device_type', 'is_active')

@admin.register(ActivityLog)
class ActivityLogAdmin(admin.ModelAdmin):
    list_display = ('timestamp', 'user', 'action_type')
    readonly_fields = ('timestamp', 'user', 'action_type', 'details')

@admin.register(CommandHistory)
class CommandHistoryAdmin(admin.ModelAdmin):
    list_display = ('description', 'user', 'device_type', 'status', 'executed_at')
    list_filter = ('status', 'device_type')
    search_fields = ('description', 'user__username', 'target_ips')
    readonly_fields = ('executed_at',)

# ==========================================
# Profile & Credentials
# ==========================================
@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'default_password')
    search_fields = ('user__username',)

@admin.register(UserProvinceCredential)
class UserProvinceCredentialAdmin(admin.ModelAdmin):
    list_display = ('user', 'province', 'sender_pass', 'receiver_pass')
    list_filter = ('province', 'user')
    search_fields = ('user__username', 'province__name')

# ==========================================
# Network Topology Links (????)
# ==========================================
@admin.register(NetworkLink)
class NetworkLinkAdmin(admin.ModelAdmin):
    list_display = ('source_bts', 'target_bts', 'link_type', 'capacity_mbps', 'is_active')
    list_filter = ('link_type', 'is_active')
    search_fields = ('source_bts__name', 'target_bts__name')