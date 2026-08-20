from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver

# ==========================================
# 1. Profile & Credentials
# ==========================================
class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    default_password = models.CharField(max_length=255, blank=True, null=True, verbose_name="Default Password")

    def __str__(self):
        return f"Profile of {self.user.username}"

class UserProvinceCredential(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='province_credentials')
    province = models.ForeignKey('Province', on_delete=models.CASCADE)
    
    sender_pass = models.CharField(max_length=255, blank=True, null=True, verbose_name="Sender Password")
    receiver_pass = models.CharField(max_length=255, blank=True, null=True, verbose_name="Receiver Password")

    class Meta:
        unique_together = ('user', 'province')

    def __str__(self):
        return f"{self.user.username} - {self.province.name} Credentials"

@receiver(post_save, sender=User)
def manage_user_profile(sender, instance, **kwargs):
    Profile.objects.get_or_create(user=instance)

# ==========================================
# 2. Main Network Models
# ==========================================
class Province(models.Model):
    name = models.CharField(max_length=50, unique=True, verbose_name="Province Name")
    mt_user = models.CharField(max_length=100, verbose_name="MikroTik User")
    mt_pass = models.CharField(max_length=100, verbose_name="MikroTik Password")
    cisco_user = models.CharField(max_length=100, verbose_name="Cisco User")
    cisco_pass = models.CharField(max_length=100, verbose_name="Cisco Password")
    mt_port = models.IntegerField(default=3100, verbose_name="MikroTik Port")
    cisco_port = models.IntegerField(default=22, verbose_name="Cisco Port")

    def __str__(self):
        return self.name

class BTS(models.Model):
    province = models.ForeignKey(Province, on_delete=models.CASCADE, related_name="bts_list")
    name = models.CharField(max_length=100, verbose_name="BTS Name")
    
    # --- FIELDS FOR LIVE MAP ---
    latitude = models.FloatField(blank=True, null=True, verbose_name="Latitude")
    longitude = models.FloatField(blank=True, null=True, verbose_name="Longitude")

    def __str__(self):
        return f"{self.province.name} - {self.name}"

class Device(models.Model):
    DEVICE_TYPES = (
        ('mikrotik', 'MikroTik'),
        ('cisco', 'Cisco Switch'),
        ('relink', 'RE-link'),
    )
    
    HARDWARE_MODELS = (
        ('QRT', 'QRT (MikroTik)'),
        ('LHG', 'LHG (MikroTik)'),
        ('Sector', 'Sector (MikroTik)'),
        ('SXT6', 'SXT 6 (MikroTik)'),
        ('CCR1009', 'CCR1009 (MikroTik)'),
        ('SXT', 'SXT (MikroTik)'),
        ('qrt5', 'QRT 5 (Old)'), 
        ('X6', 'XC6 (RE-link)'),
        ('X7', 'XC7 (RE-link)'),
        ('LDF', 'LDF (RE-link)'),
        ('xc6', 'XC6 (Old)'), 
        ('xc7', 'XC7 (Old)'), 
        ('2960', 'Cisco 2960'),
    )
    
    bts = models.ForeignKey(BTS, on_delete=models.CASCADE, related_name="devices")
    device_type = models.CharField(max_length=20, choices=DEVICE_TYPES, verbose_name="Device Type")
    
    name = models.CharField(max_length=150, blank=True, null=True, verbose_name="Device Name")
    ip_address = models.GenericIPAddressField(verbose_name="IP Address")
    mac_address = models.CharField(max_length=50, verbose_name="MAC Address")
    
    has_adapter = models.BooleanField(default=False, verbose_name="Adapter")
    has_poe = models.BooleanField(default=False, verbose_name="POE")
    
    device_model = models.CharField(max_length=20, choices=HARDWARE_MODELS, blank=True, null=True, verbose_name="Device Model")
    
    ssid = models.CharField(max_length=100, blank=True, null=True, verbose_name="SSID")
    frequency = models.CharField(max_length=50, blank=True, null=True, verbose_name="Frequency")

    def __str__(self):
        if self.name:
            return f"{self.name} - {self.ip_address} ({self.get_device_type_display()})"
        return f"{self.ip_address} ({self.get_device_type_display()}) - {self.bts.name}"

class ConfigCommand(models.Model):
    DEVICE_TYPES = (
        ('mikrotik', 'MikroTik'),
        ('cisco', 'Cisco'),
    )
    device_type = models.CharField(max_length=20, choices=DEVICE_TYPES)
    command_order = models.IntegerField(default=1, verbose_name="Execution Order")
    command_text = models.TextField(verbose_name="Command Text")
    is_active = models.BooleanField(default=True, verbose_name="Is Active")

    class Meta:
        ordering = ['command_order']

    def __str__(self):
        return f"[{self.device_type}] {self.command_order}: {self.command_text[:30]}"

class ActivityLog(models.Model):
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    action_type = models.CharField(max_length=100)
    details = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        permissions = [
            ("can_run_config", "Can run config"),
            ("can_view_reports", "Can view reports"),
            ("can_search_mac", "Can search MAC"),
            ("can_check_signal", "Can check signals"),
        ]

    def __str__(self):
        return f"{self.timestamp.strftime('%Y-%m-%d %H:%M')} - {self.user} - {self.action_type}"

class CommandHistory(models.Model):
    STATUS_CHOICES = [
        ('Pending', 'Pending'),
        ('Running', 'Running'),
        ('Completed', 'Completed'),
        ('Failed', 'Failed'),
        ('Rejected', 'Rejected'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    description = models.CharField(max_length=255, verbose_name="Description")
    commands = models.TextField(verbose_name="Commands")
    device_type = models.CharField(max_length=50, default='mikrotik')
    
    target_ips = models.TextField(blank=True, null=True, verbose_name="Target IPs") 
    output_log = models.TextField(blank=True, null=True, verbose_name="Output Log") 
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Pending', verbose_name="Status")
    executed_at = models.DateTimeField(auto_now_add=True, verbose_name="Execution Time")

    total_devices = models.IntegerField(default=0, verbose_name="Total Devices")
    completed_devices = models.IntegerField(default=0, verbose_name="Completed Devices")
    progress_percentage = models.IntegerField(default=0, verbose_name="Progress Percentage")

    def __str__(self):
        return f"{self.description} by {self.user} [{self.status}]"

# ==========================================
# 3. Employee Connection Logs
# ==========================================
class ConnectionLog(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name="Employee")
    province = models.ForeignKey(Province, on_delete=models.SET_NULL, null=True, verbose_name="Province")
    ip_address = models.CharField(max_length=50, verbose_name="Device IP")
    device_type = models.CharField(max_length=20, verbose_name="Device Type (Sender/Receiver)")
    is_online = models.BooleanField(default=False, verbose_name="Ping Status")
    timestamp = models.DateTimeField(auto_now_add=True, verbose_name="Connection Time")

    class Meta:
        ordering = ['-timestamp'] 

    def __str__(self):
        return f"{self.user.username} connected to {self.ip_address} ({self.device_type})"

# ==========================================
# 4. Network Topology & Links (Map)
# ==========================================
class NetworkLink(models.Model):
    LINK_TYPES = (
        ('wireless', 'Wireless (Microwave/Radio)'),
        ('fiber', 'Fiber Optic'),
    )
    
    # ??? ????
    source_bts = models.ForeignKey(BTS, on_delete=models.CASCADE, related_name='outgoing_links', verbose_name="Source BTS")
    
    # ??? ????
    target_bts = models.ForeignKey(BTS, on_delete=models.CASCADE, related_name='incoming_links', verbose_name="Target BTS")
    
    # ??? ??????
    link_type = models.CharField(max_length=20, choices=LINK_TYPES, default='wireless', verbose_name="Link Type")
    
    # ????? ???? ???? SNMP ?? ?????
    capacity_mbps = models.IntegerField(default=1000, help_text="Total link capacity in Mbps", verbose_name="Capacity (Mbps)")
    
    # ????? ???? (????/????? ???? ??? ????)
    is_active = models.BooleanField(default=True, verbose_name="Is Active")

    def __str__(self):
        return f"{self.source_bts.name} <--> {self.target_bts.name} ({self.get_link_type_display()})"