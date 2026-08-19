import routeros_api
import logging

logger = logging.getLogger(__name__)

def run_mikrotik(host, commands, user, password, port):
    connection = None
    try:
        connection = routeros_api.RouterOsApiPool(
            host=host, username=user, password=password,
            port=port, plaintext_login=True
        )
        api = connection.get_api()

        executed_any = False
        skipped_all = True
        log_messages = []

        if isinstance(commands, dict):
            command_list = commands.values()
        else:
            command_list = commands

        for command in command_list:
            command = command.strip()
            if not command:
                continue

            # ==========================================
            # پارسر هوشمند برای تبدیل زبان ترمینال به API
            # ==========================================
            parts = command.split()
            
            args = {}
            path_action_parts = []
            
            # جدا کردن آرگومان‌ها (متغیرهایی که = دارند) از مسیر اصلی
            for p in parts:
                if "=" in p:
                    k, v = p.split("=", 1)
                    args[k] = v
                else:
                    path_action_parts.append(p)
            
            if len(path_action_parts) < 2:
                msg = f"❌ Invalid command format: {command}"
                logger.error(msg)
                log_messages.append(msg)
                continue

            # در دستورات میکروتیک، همیشه آخرین کلمه‌ی قبل از آرگومان‌ها، اکشن است (مثل set یا add)
            action = path_action_parts[-1]
            
            # بقیه کلمات، مسیر API هستند (تبدیل system identity به /system/identity)
            clean_path_parts = [p.strip('/') for p in path_action_parts[:-1]]
            resource_path = "/" + "/".join(clean_path_parts)
            # ==========================================

            resource = api.get_resource(resource_path)

            try:
                existing = resource.get(**args)
                if existing:
                    msg = f"⏭️ Skipped: {command}"
                    logger.warning(f"{msg} on {host}")
                    log_messages.append(msg)
                    continue
            except Exception:
                pass

            getattr(resource, action)(**args)
            msg_success = f"✅ Executed: {command}"
            logger.info(f"{msg_success} on {host}")
            log_messages.append(msg_success)
            executed_any = True
            skipped_all = False

        if executed_any:
            return {"status": "success", "host": host, "message": "done", "logs": log_messages}
        elif skipped_all:
            return {"status": "warning", "host": host, "message": "skip", "logs": log_messages}
        else:
            return {"status": "error", "host": host, "message": "No valid commands executed.", "logs": log_messages}

    except Exception as e:
        error_msg = f"❌ Error on {host}: {e}"
        logger.error(error_msg)
        return {"status": "error", "host": host, "message": str(e), "logs": []}
        
    finally:
        # این بخش بسیار مهم است: تحت هر شرایطی اتصال را قطع می‌کند
        if connection:
            try:
                connection.disconnect()
            except Exception:
                pass


def report_customers(host, user, password, port):
    connection = None
    try:
        connection = routeros_api.RouterOsApiPool(
            host=host, username=user, password=password,
            port=port, plaintext_login=True
        )
        api = connection.get_api()
        wireless_access = api.get_resource("/interface/wireless/access-list")
        count = len(wireless_access.get())
        return {"status": "success", "host": host, "count": count}
    except Exception as e:
        logger.error(f"❌ Error on {host}: {e}")
        return {"status": "error", "host": host, "error": str(e)}
    finally:
        if connection:
            try:
                connection.disconnect()
            except Exception:
                pass


def report_signal_strength(host, user, password, port, threshold):
    connection = None
    try:
        connection = routeros_api.RouterOsApiPool(
            host=host, username=user, password=password,
            port=port, plaintext_login=True
        )
        api = connection.get_api()
        reg_table = api.get_resource("/interface/wireless/registration-table")
        clients = reg_table.get()

        weak_clients = []

        for c in clients:
            name = c.get("comment") or c.get("radio-name") or c.get("mac-address", "unknown")
            signal = c.get("signal-strength", "")
            
            if signal:
                try:
                    signal_value = int(signal.replace("dBm", "").strip())
                except ValueError:
                    continue

                if signal_value <= threshold:
                    weak_clients.append({
                        "name": name,
                        "signal": signal,
                        "value": signal_value
                    })
                    
        return {
            "status": "success", 
            "host": host, 
            "weak_clients": weak_clients,
            "count": len(weak_clients)
        }

    except Exception as e:
        logger.error(f"❌ Error on {host}: {e}")
        return {"status": "error", "host": host, "error": str(e)}
    finally:
        if connection:
            try:
                connection.disconnect()
            except Exception:
                pass