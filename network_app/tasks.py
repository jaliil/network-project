from celery import shared_task
from concurrent.futures import ThreadPoolExecutor
from .models import CommandHistory
from .utils.mikrotik import run_mikrotik
from .utils.cisco import run_cisco_web  # ?? ??? ???? ????? ?? ????? ????? ??

@shared_task
def execute_network_commands(history_id, ips_list, username, password, port, commands, device_type):
    try:
        history = CommandHistory.objects.get(id=history_id)
    except CommandHistory.DoesNotExist:
        return "History not found."

    def process_single_ip(ip):
        try:
            if device_type == 'mikrotik':
                return run_mikrotik(ip, commands, username, password, port)
            else:
                return run_cisco_web(ip, commands, username, password, port)  # ?? ????? ?? ????? ??
        except Exception as e:
            return {"status": "error", "host": ip, "message": str(e)}

    # ?????? ????? ?? ?????? ?? ???? ?????? (???? ????? ?????? ???)
    with ThreadPoolExecutor(max_workers=20) as executor:
        results = list(executor.map(process_single_ip, ips_list))

    history.status = 'Completed'
    history.save()

    return f"Processed {len(ips_list)} devices rapidly."