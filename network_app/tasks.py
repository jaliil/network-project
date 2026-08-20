import time
from django.utils import timezone
from django.core.cache import cache
from celery import shared_task
from concurrent.futures import ThreadPoolExecutor, as_completed

from .models import CommandHistory, NetworkLink
from .utils.mikrotik import run_mikrotik
from .utils.cisco import run_cisco_web
from .utils.snmp_tools import get_snmp_traffic

# ==========================================
# Task 1: ????? ?????? ??????? ?????? ?? ???? ????
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
# Task 2: ?????????? ???? ?????? ??????? ?? ???? SNMP
# ==========================================
@shared_task
def update_network_links_traffic():
    """
    ??? ??? ?? ??? ????? ?????? ???? ?????? ? ?????? ??????? ??????? ?? ?????? ? ????? ??????.
    """
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