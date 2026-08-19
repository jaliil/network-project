from netmiko import ConnectHandler
import logging

logger = logging.getLogger(__name__)

# ==========================================
# ????? ????? ??
# ==========================================
def report_switch_web(host, user, password, port):
    net_connect = None
    try:
        device = {
            "device_type": "cisco_ios",
            "ip": host,
            "username": user,
            "password": password,
            "port": port,
            # "global_delay_factor": 2  # ?? ???? ??? ???? ??????? ??? ?? ?? ????? ???????
        }
        net_connect = ConnectHandler(**device)
        output = net_connect.send_command("show interfaces status")
        
        issue_ports = []
        lines = output.splitlines()

        # ????? ?? ?? ?? ????? ???????
        for line in lines[1:]:
            parts = line.split()
            if len(parts) < 6:
                continue

            port_name = parts[0]
            description = parts[1]
            try:
                duplex = parts[4].lower()
                speed = parts[5].lower()
            except IndexError:
                continue

            # ???? ???? ???????? ????????
            if speed == "a-10" or duplex == "half":
                issue_ports.append({
                    "port": port_name,
                    "desc": description,
                    "duplex": duplex,
                    "speed": speed
                })

        status = "has issue" if issue_ports else "normal"

        return {
            "status": "success",
            "host": host,
            "switch_status": status,
            "issue_ports": issue_ports
        }

    except Exception as e:
        logger.error(f"? Error on {host}: {e}")
        return {
            "status": "error",
            "host": host,
            "error": str(e)
        }
    finally:
        # ??? ??? ??? ????? ??? ?? ?? ??? ??? (?? ??? VTY) ???? ??????
        if net_connect:
            try:
                net_connect.disconnect()
            except Exception:
                pass


# ==========================================
# ????? ????? ?????
# ==========================================
def run_cisco_web(host, commands_list, user, password, port):
    net_connect = None
    try:
        device = {
            "device_type": "cisco_ios",
            "ip": host,
            "username": user,
            "password": password,
            "port": port,
        }
        net_connect = ConnectHandler(**device)
        
        # ???? ?? ??? Enable (??? ???? ??? ???????? priv 15 ????? ???? secret ?? ?? device ???? ????? ???)
        net_connect.enable()

        output = net_connect.send_config_set(commands_list)
        
        # ????? ?????? ???????
        net_connect.save_config()
        
        return {
            "status": "success",
            "host": host,
            "output": output
        }
    except Exception as e:
        logger.error(f"? Error on {host}: {e}")
        return {
            "status": "error",
            "host": host,
            "error": str(e)
        }
    finally:
        # ??? ??? ????? ??? ?? ??????
        if net_connect:
            try:
                net_connect.disconnect()
            except Exception:
                pass