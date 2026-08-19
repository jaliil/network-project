from django.contrib import admin
from .models import Province, BTS, Device, ConfigCommand, ActivityLog, Profile, CommandHistory, UserProvinceCredential

@admin.register(Province)
class ProvinceAdmin(admin.ModelAdmin):
    list_display = ('name', 'mt_user', 'cisco_user', 'mt_port', 'cisco_port')

@admin.register(BTS)
class BTSAdmin(admin.ModelAdmin):
    list_display = ('name', 'province')
    list_filter = ('province',)

@admin.register(Device)
class DeviceAdmin(admin.ModelAdmin):
    list_display = ('ip_address', 'device_type', 'bts', 'mac_address')
    list_filter = ('device_type', 'bts__province', 'bts')
    search_fields = ('ip_address', 'mac_address')

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
# ??????? ? ???????? ????? ???
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