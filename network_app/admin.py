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
# Network Topology Links (Map)
# ==========================================
@admin.register(NetworkLink)
class NetworkLinkAdmin(admin.ModelAdmin):
    list_display = ('id', 'source_bts', 'target_bts', 'link_type', 'capacity_mbps', 'is_active')
    list_filter = ('link_type', 'is_active', 'source_device_type', 'target_device_type')
    search_fields = ('source_bts__name', 'target_bts__name', 'source_ip', 'target_ip')

    # ??? ???? ???????? ?? ???? ???? ??????? ???????? ????? ???? (???-???????)
    readonly_fields = ('current_tx_mbps', 'current_rx_mbps', 'last_snmp_update')

    # ????????? ? ???????? ??? ???? ??? ?????
    fieldsets = (
        ('1. Source (Sender) Information', {
            'fields': ('source_bts', 'source_device_type', 'source_ip', 'source_interface', 'snmp_community'),
            'classes': ('wide',)
        }),
        ('2. Target (Receiver) Information', {
            'fields': ('target_bts', 'target_device_type', 'target_ip', 'target_interface', 'target_snmp_community'),
            'classes': ('wide',)
        }),
        ('3. Link Specifications', {
            'fields': ('link_type', 'capacity_mbps', 'is_active'),
        }),
        ('4. Live Traffic (Auto-Updated by System)', {
            'fields': ('current_tx_mbps', 'current_rx_mbps', 'last_snmp_update'),
            'classes': ('collapse',) # ??? ??? ?? ???? ????? ???? ??? ?? ??? ?????? ????
        }),
    )