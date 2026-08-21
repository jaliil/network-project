import time
import re
import logging
from django.utils import timezone
from django.core.cache import cache
from celery import shared_task
from concurrent.futures import ThreadPoolExecutor, as_completed
from netmiko import ConnectHandler

from .models import CommandHistory, NetworkLink
from .utils.mikrotik import run_mikrotik
from .utils.cisco import run_cisco_web
from .utils.snmp_tools import get_snmp_traffic

logger = logging.getLogger(__name__)

# ==========================================
# Task 1: اجرای دستورات شبکه روی چند آی‌پی
# ==========================================
@shared_task
def execute_network_commands(history_id, ips_list, username, password, port, commands, device_type):
    try:
        history = CommandHistory.objects.get(id=history_id)
    except CommandHistory.DoesNotExist:
        return "History not found."

    total_devices = len(ips_list)
    
    history.total_devices = total_devices
    history.completed_devices = 0
    history.progress_percentage = 0
    history.save()

    def process_single_ip(ip):
        try:
            if device_type == 'mikrotik':
                return run_mikrotik(ip, commands, username, password, port)
            else:
                return run_cisco_web(ip, commands, username, password, port)
        except Exception as e:
            return {"status": "error", "host": ip, "message": str(e)}

    results = []
    
    with ThreadPoolExecutor(max_workers=20) as executor:
        future_to_ip = {executor.submit(process_single_ip, ip): ip for ip in ips_list}
        
        for future in as_completed(future_to_ip):
            ip = future_to_ip[future]
            try:
                result = future.result()
                results.append(result)
            except Exception as e:
                results.append({"status": "error", "host": ip, "message": str(e)})
            
            history.completed_devices += 1
            
            if total_devices > 0:
                percent = int((history.completed_devices / total_devices) * 100)
                history.progress_percentage = percent
            
            history.save()

    history.status = 'Completed'
    history.progress_percentage = 100
    history.save()

    return f"Processed {total_devices} devices rapidly."


# ==========================================
# Task 2: بروزرسانی زنده ترافیک لینک‌ها از طریق SNMP
# ==========================================
@shared_task
def update_network_links_traffic():
    links = NetworkLink.objects.filter(
        is_active=True, 
        source_ip__isnull=False, 
        source_interface__isnull=False
    )
    
    for link in links:
        ip = link.source_ip
        community = link.snmp_community
        interface = link.source_interface
        
        if not ip:
            continue
            
        traffic = get_snmp_traffic(ip, community, interface)
        
        if traffic:
            rx_bytes, tx_bytes = traffic
            current_time = time.time()
            
            cache_key = f"link_traffic_{link.id}"
            prev_data = cache.get(cache_key)
            
            if prev_data:
                prev_rx, prev_tx, prev_time = prev_data
                time_diff = current_time - prev_time
                
                if time_diff > 0:
                    rx_mbps = ((rx_bytes - prev_rx) * 8) / (time_diff * 1024 * 1024)
                    tx_mbps = ((tx_bytes - prev_tx) * 8) / (time_diff * 1024 * 1024)
                    
                    if rx_mbps >= 0 and tx_mbps >= 0:
                        link.current_rx_mbps = round(rx_mbps, 2)
                        link.current_tx_mbps = round(tx_mbps, 2)
                        link.last_snmp_update = timezone.now()
                        link.save(update_fields=['current_rx_mbps', 'current_tx_mbps', 'last_snmp_update'])
            
            cache.set(cache_key, (rx_bytes, tx_bytes, current_time), timeout=600)
            
    return f"Updated traffic for {links.count()} links."


# ==========================================
# 🔴 Task 3: اتوماسیون MAC-Telnet برای دستگاه‌های لایه ۲ (CPE)
# ==========================================
@shared_task
def execute_cpe_mac_commands(history_id, sender_ip, sender_username, sender_password, sender_port, commands):
    try:
        history = CommandHistory.objects.get(id=history_id)
    except CommandHistory.DoesNotExist:
        return "History not found."

    # استخراج یوزر و پسورد کلاینت از توضیحات (که در views ذخیره کردیم)
    cpe_user, cpe_pass = sender_username, sender_password # پیش‌فرض: یوزر و رمزِ دستگاه مادر
    desc_parts = history.description.split('| CPE_CREDS:')
    clean_description = desc_parts[0].strip()

    if len(desc_parts) > 1:
        creds = desc_parts[1].split(':')
        if len(creds) == 2:
            cpe_user = creds[0].strip() if creds[0].strip() else sender_username
            cpe_pass = creds[1].strip() if creds[1].strip() else sender_password

    # پاک کردن یوزر و رمز از دیتابیس برای امنیت و زیبایی پنل
    history.description = clean_description
    history.save()

    device = {
        'device_type': 'mikrotik_routeros',
        'host': sender_ip,
        'username': sender_username,
        'password': sender_password,
        'port': sender_port,
    }

    try:
        # ۱. اتصال به دستگاه مادر (Sender)
        conn = ConnectHandler(**device)
        
        # ۲. استخراج تمام MAC Address های متصل به وایرلس
        output = conn.send_command('interface wireless registration-table print')
        # پیدا کردن الگوی مک‌آدرس با Regex
        macs = list(set(re.findall(r'(?:[0-9A-Fa-f]{2}:){5}[0-9A-Fa-f]{2}', output, re.IGNORECASE)))

        if not macs:
            history.status = 'Completed'
            history.description += " (No active wireless clients found)"
            history.save()
            conn.disconnect()
            return "No clients found."

        history.total_devices = len(macs)
        history.completed_devices = 0
        history.progress_percentage = 0
        history.save()

        # ۳. ورود به تک‌تک کلاینت‌ها با مک‌تلنت
        for mac in macs:
            try:
                # دستور مک‌تلنت به میکروتیک
                conn.write_channel(f"/tool mac-telnet {mac}\r\n")
                time.sleep(2)
                out = conn.read_channel()

                # اگر یوزر خواست:
                if "Login:" in out:
                    conn.write_channel(f"{cpe_user}\r\n")
                    time.sleep(1)
                    out += conn.read_channel()

                # اگر پسورد خواست:
                if "Password:" in out:
                    conn.write_channel(f"{cpe_pass}\r\n")
                    time.sleep(1)

                time.sleep(1)
                conn.write_channel("\r\n") # زدن اینتر برای گرفتن Prompt کلاینت
                time.sleep(0.5)

                # اجرای کامندهای درخواستی کاربر
                for cmd in commands:
                    if cmd.strip():
                        conn.write_channel(f"{cmd.strip()}\r\n")
                        time.sleep(0.5)

                # خروج ایمن از مک‌تلنت
                conn.write_channel("quit\r\n")
                time.sleep(1)
                # در صورت گیر کردن، زدن دکمه Ctrl+C برای خروج
                conn.write_channel("\x03")
                time.sleep(0.5)
                # خالی کردن بافر
                conn.read_channel()

            except Exception as inner_e:
                logger.error(f"Failed MAC-Telnet to {mac}: {str(inner_e)}")
                # اگر در یک کلاینت گیر کرد، ارتباط با Ctrl+C ریست شود تا سراغ بعدی برود
                conn.write_channel("\x03\r\n")
                time.sleep(1)

            history.completed_devices += 1
            history.progress_percentage = int((history.completed_devices / history.total_devices) * 100)
            history.save()

        conn.disconnect()
        history.status = 'Completed'
        history.progress_percentage = 100
        history.save()
        return f"Successfully executed on {len(macs)} MACs via {sender_ip}"

    except Exception as e:
        history.status = 'Rejected'
        history.description += f" [Connection Error: {str(e)}]"
        history.save()
        return f"Error: {str(e)}"