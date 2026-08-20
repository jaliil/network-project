from celery import shared_task
from concurrent.futures import ThreadPoolExecutor, as_completed
from .models import CommandHistory
from .utils.mikrotik import run_mikrotik
from .utils.cisco import run_cisco_web

@shared_task
def execute_network_commands(history_id, ips_list, username, password, port, commands, device_type):
    try:
        history = CommandHistory.objects.get(id=history_id)
    except CommandHistory.DoesNotExist:
        return "History not found."

    total_devices = len(ips_list)
    
    # 1. ???????? ????? ???? ???? ??????
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
    
    # 2. ????? ?????? ?? ?????? ?????? ??????? (Live Progress)
    with ThreadPoolExecutor(max_workers=20) as executor:
        # ????? ???? ????? ?? ????? ????? (Threads)
        future_to_ip = {executor.submit(process_single_ip, ip): ip for ip in ips_list}
        
        # ?? ??? ????? ??? ?? ?????? ???? ?? (??? ???? ???? ??? ???? ???):
        for future in as_completed(future_to_ip):
            ip = future_to_ip[future]
            try:
                result = future.result()
                results.append(result)
            except Exception as e:
                results.append({"status": "error", "host": ip, "message": str(e)})
            
            # 3. ????? ???? ?????? ?? ???????
            history.completed_devices += 1
            
            # ?????? ???? ??????
            if total_devices > 0:
                percent = int((history.completed_devices / total_devices) * 100)
                # ???? ????? ???? ?????? ?? 100% ?? ???
                history.progress_percentage = percent
            
            history.save()

    # 4. ????? ???
    history.status = 'Completed'
    history.progress_percentage = 100
    history.save()

    return f"Processed {total_devices} devices rapidly."