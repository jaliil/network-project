import routeros_api
from netmiko import ConnectHandler

def search_mac_in_network(host_list, dev_type, mac_query, username, password, port):
    """
    جستجوی یک مک آدرس خاص در لیستی از آی‌پی‌ها.
    این تابع خروجی را به صورت دیکشنری برای نمایش در وب برمی‌گرداند.
    """
    mac_query = mac_query.strip().lower()
    errors = [] # لیستی برای ذخیره خطاهای اتصال به دستگاه‌ها

    # ==========================================
    # جستجو در تجهیزات MikroTik
    # ==========================================
    if dev_type in ["mt", "mikrotik"]:
        for ip in host_list:
            try:
                connection = routeros_api.RouterOsApiPool(
                    host=ip, 
                    username=username, 
                    password=password,
                    port=port, 
                    plaintext_login=True
                )
                api = connection.get_api()
                iface = api.get_resource("/interface/ethernet")
                ether1 = iface.get(name="ether1")[0]
                mac = ether1.get("mac-address", "").lower()
                connection.disconnect()
                
                # اگر مک آدرس پیدا شد، بلافاصله نتیجه موفقیت‌آمیز را برگردان
                if mac == mac_query:
                    return {
                        "status": "success", 
                        "ip": ip, 
                        "mac": mac, 
                        "message": f"✅ دستگاه میکروتیک با موفقیت پیدا شد!"
                    }
            except Exception as e:
                errors.append(f"{ip}: {str(e)}")
                
        # اگر حلقه تمام شد و چیزی پیدا نشد
        return {
            "status": "not_found", 
            "message": "❌ هیچ دستگاه میکروتیکی با این مک آدرس یافت نشد.", 
            "errors": errors
        }

    # ==========================================
    # جستجو در تجهیزات Cisco
    # ==========================================
    elif dev_type == "cisco":
        for ip in host_list:
            try:
                device_config = {
                    "device_type": "cisco_ios",
                    "ip": ip,
                    "username": username,
                    "password": password,
                    "port": port,
                }
                net_connect = ConnectHandler(**device_config)
                net_connect.enable()
                output = net_connect.send_command("show version")
                net_connect.disconnect()

                for line in output.splitlines():
                    if "Base ethernet MAC Address" in line:
                        base_mac = line.split(":")[-1].strip().lower()
                        if base_mac == mac_query:
                            return {
                                "status": "success", 
                                "ip": ip, 
                                "mac": base_mac, 
                                "message": f"✅ سوییچ سیسکو با موفقیت پیدا شد!"
                            }
            except Exception as e:
                errors.append(f"{ip}: {str(e)}")
                
        return {
            "status": "not_found", 
            "message": "❌ هیچ سوییچ سیسکویی با این مک آدرس یافت نشد.", 
            "errors": errors
        }
    
    # اگر نوع دستگاه اشتباه پاس داده شده بود
    return {"status": "error", "message": "⚠️ نوع دستگاه نامعتبر است."}