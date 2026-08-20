import json
import openpyxl
import subprocess
import platform
from datetime import timedelta
from openpyxl.styles import Font, PatternFill, Alignment
from openpyxl.utils import get_column_letter

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.sessions.models import Session
from django.utils import timezone
from django.contrib.auth.models import User
from django.contrib.auth.views import LoginView
from django.contrib import messages
from django.http import HttpResponse, JsonResponse
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.db.models import Q

from .models import Device, BTS, ActivityLog, Province, CommandHistory, UserProvinceCredential, ConnectionLog, NetworkLink
from .forms import DeviceForm

from .tasks import execute_network_commands
from .utils.search import search_mac_in_network
from .utils.mikrotik import report_signal_strength, report_customers
from .utils.cisco import run_cisco_web, report_switch_web
from .utils.snmp_tools import get_snmp_traffic, get_device_interfaces


def get_base_context():
    pending = list(CommandHistory.objects.filter(status='Pending').order_by('-executed_at'))
    return {
        'pending_tasks': pending,
        'notifications': pending, 
    }

class CustomLoginView(LoginView):
    template_name = 'registration/login.html'

@login_required(login_url='/login/')
def dashboard_view(request):
    if request.user.groups.filter(name='employee_user').exists():
        return redirect('employee_panel')

    sessions = Session.objects.filter(expire_date__gte=timezone.now())
    uid_list = [session.get_decoded().get('_auth_user_id') for session in sessions if session.get_decoded().get('_auth_user_id')]
    
    online_users = User.objects.filter(id__in=uid_list)
    total_users_count = User.objects.count()
    
    provinces = Province.objects.all()
    device_types = Device.DEVICE_TYPES
    
    chart_data = {}
    for prov in provinces:
        prov_data = {}
        for dev_val, dev_name in device_types:
            prov_data[dev_val] = Device.objects.filter(bts__province=prov, device_type=dev_val).count()
        chart_data[prov.name] = prov_data

    today_dt = timezone.localtime(timezone.now())
    today_date = today_dt.date()
    
    chart_labels = []
    mikrotik_trend = [0] * 30
    cisco_trend = [0] * 30
    
    for i in range(29, -1, -1):
        target_d = today_date - timedelta(days=i)
        chart_labels.append(target_d.strftime('%b %d'))
        
    start_dt = today_dt - timedelta(days=29)
    start_dt = start_dt.replace(hour=0, minute=0, second=0, microsecond=0)
    
    recent_tasks = CommandHistory.objects.filter(executed_at__gte=start_dt)
    
    for task in recent_tasks:
        if task.executed_at:
            try:
                t_date = timezone.localtime(task.executed_at).date()
            except:
                t_date = task.executed_at.date() if hasattr(task.executed_at, 'date') else None
                
            if t_date:
                day_diff = (today_date - t_date).days
                idx = 29 - day_diff
                if 0 <= idx <= 29:
                    if task.device_type == 'mikrotik':
                        mikrotik_trend[idx] += 1
                    elif task.device_type == 'cisco':
                        cisco_trend[idx] += 1
    
    usage_trend_data = json.dumps({
        'labels': chart_labels,
        'mikrotik': mikrotik_trend,
        'cisco': cisco_trend
    })

    pending_mikrotik = CommandHistory.objects.filter(device_type='mikrotik', status='Pending').count()
    done_mikrotik = CommandHistory.objects.filter(device_type='mikrotik', status='Completed').count()
    pending_cisco = CommandHistory.objects.filter(device_type='cisco', status='Pending').count()
    done_cisco = CommandHistory.objects.filter(device_type='cisco', status='Completed').count()

    context = get_base_context()
    context.update({
        'online_users': online_users, 
        'total_users_count': total_users_count,
        'provinces': provinces,
        'device_chart_data': json.dumps(chart_data), 
        'device_types': device_types, 
        'pending_mikrotik': pending_mikrotik,
        'done_mikrotik': done_mikrotik, 
        'pending_cisco': pending_cisco, 
        'done_cisco': done_cisco,
        'usage_trend_data': usage_trend_data,
    })
    return render(request, 'dashboard.html', context)

@login_required(login_url='/login/')
def run_mikrotik_view(request):
    searched_prov, entered_commands, entered_description = None, "", ""
    if request.method == 'POST':
        prov_id = request.POST.get('province')
        bts_ids = request.POST.getlist('bts')
        site_ips = request.POST.getlist('site') 
        description = request.POST.get('description', '')
        commands_text = request.POST.get('commands', '')
        entered_commands, entered_description = commands_text, description
        if prov_id and commands_text.strip():
            try:
                searched_prov = Province.objects.get(id=prov_id)
                if site_ips and any(ip.strip() for ip in site_ips):
                    valid_ips = [ip.strip() for ip in site_ips if ip.strip()]
                    devices = Device.objects.filter(ip_address__in=valid_ips, device_type='mikrotik')
                elif bts_ids and any(bts.strip() for bts in bts_ids):
                    valid_bts = [bts.strip() for bts in bts_ids if bts.strip()]
                    devices = Device.objects.filter(bts_id__in=valid_bts, device_type='mikrotik')
                else:
                    devices = Device.objects.filter(bts__province=searched_prov, device_type='mikrotik')
                ips_list = [dev.ip_address for dev in devices if dev.ip_address]
                if ips_list:
                    CommandHistory.objects.create(
                        user=request.user, description=description, commands=commands_text, 
                        device_type='mikrotik', target_ips=",".join(ips_list), 
                        status='Pending', total_devices=len(ips_list)
                    )
                    messages.success(request, f"Request for {len(ips_list)} devices submitted to DCN for approval.")
                else:
                    messages.warning(request, "No devices found matching these criteria.")
            except Exception as e:
                messages.error(request, f"Error: {str(e)}")

    context = get_base_context()
    context.update({
        'provinces': Province.objects.all(), 'btss': BTS.objects.select_related('province').all(), 
        'histories': CommandHistory.objects.filter(device_type='mikrotik').order_by('-executed_at')[:15], 
        'searched_prov': searched_prov, 'entered_commands': entered_commands, 'entered_description': entered_description
    })
    return render(request, 'run_mikrotik.html', context)

@login_required(login_url='/login/')
def run_cisco_view(request):
    searched_prov, entered_commands, entered_description = None, "", ""
    if request.method == 'POST':
        prov_id = request.POST.get('province')
        bts_ids = request.POST.getlist('bts')
        site_ips = request.POST.getlist('site') 
        description = request.POST.get('description', '')
        commands_text = request.POST.get('commands', '')
        entered_commands, entered_description = commands_text, description
        if prov_id and commands_text.strip():
            try:
                searched_prov = Province.objects.get(id=prov_id)
                if site_ips and any(ip.strip() for ip in site_ips):
                    valid_ips = [ip.strip() for ip in site_ips if ip.strip()]
                    devices = Device.objects.filter(ip_address__in=valid_ips, device_type='cisco')
                elif bts_ids and any(bts.strip() for bts in bts_ids):
                    valid_bts = [bts.strip() for bts in bts_ids if bts.strip()]
                    devices = Device.objects.filter(bts_id__in=valid_bts, device_type='cisco')
                else:
                    devices = Device.objects.filter(bts__province=searched_prov, device_type='cisco')
                ips_list = [dev.ip_address for dev in devices if dev.ip_address]
                if ips_list:
                    CommandHistory.objects.create(
                        user=request.user, description=description, commands=commands_text, 
                        device_type='cisco', target_ips=",".join(ips_list), 
                        status='Pending', total_devices=len(ips_list)
                    )
                    messages.success(request, f"Request for {len(ips_list)} devices submitted to DCN for approval.")
                else:
                    messages.warning(request, "No devices found matching these criteria.")
            except Exception as e:
                messages.error(request, f"Error: {str(e)}")

    context = get_base_context()
    context.update({
        'provinces': Province.objects.all(), 'btss': BTS.objects.select_related('province').all(), 
        'histories': CommandHistory.objects.filter(device_type='cisco').order_by('-executed_at')[:15], 
        'searched_prov': searched_prov, 'entered_commands': entered_commands, 'entered_description': entered_description
    })
    return render(request, 'run_cisco.html', context)

@login_required(login_url='/login/')
def approve_command_view(request, history_id):
    history = get_object_or_404(CommandHistory, id=history_id)
    if history.status == 'Pending':
        history.status = 'Running'
        history.save()
        ips_list = history.target_ips.split(',')
        dev = Device.objects.filter(ip_address=ips_list[0]).first()
        prov = dev.bts.province
        raw_commands = [cmd.strip() for cmd in history.commands.split('\n') if cmd.strip()]
        if history.device_type == 'mikrotik': 
            execute_network_commands.delay(history_id=history.id, ips_list=ips_list, username=prov.mt_user, password=prov.mt_pass, port=prov.mt_port, commands=raw_commands, device_type='mikrotik')
        else: 
            execute_network_commands.delay(history_id=history.id, ips_list=ips_list, username=prov.cisco_user, password=prov.cisco_pass, port=prov.cisco_port, commands=raw_commands, device_type='cisco')
        messages.success(request, "Request approved and running in background.")
    return redirect(request.META.get('HTTP_REFERER', 'dashboard'))

@login_required(login_url='/login/')
def reject_command_view(request, history_id):
    history = get_object_or_404(CommandHistory, id=history_id)
    if history.status == 'Pending':
        history.status = 'Rejected'
        history.save()
        messages.success(request, "Request rejected successfully.")
    return redirect(request.META.get('HTTP_REFERER', 'dashboard'))

@login_required(login_url='/login/')
def add_device_view(request):
    if request.method == 'POST':
        form = DeviceForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Device saved successfully!')
            return redirect(request.path)
    else: 
        form = DeviceForm()
    context = get_base_context()
    context.update({
        'form': form, 'last_device': Device.objects.order_by('-id').first(), 
        'provinces': Province.objects.all(), 'bts_list': BTS.objects.select_related('province').all()
    })
    return render(request, 'add_device.html', context)

@login_required(login_url='/login/')
def bulk_upload_view(request):
    if request.method == 'POST' and request.FILES.get('excel_file'):
        try:
            wb = openpyxl.load_workbook(request.FILES['excel_file'])
            ws = wb.active
            count = 0
            for row in ws.iter_rows(min_row=2, values_only=True):
                bts_name, dev_type, ip, mac, mt_model, rl_model, ssid, freq = row
                if bts_name and dev_type and ip and mac:
                    bts_obj = BTS.objects.filter(name=bts_name).first()
                    if bts_obj:
                        Device.objects.create(bts=bts_obj, device_type=dev_type, ip_address=ip, mac_address=mac, device_model=mt_model or rl_model, ssid=ssid, frequency=freq)
                        count += 1
            messages.success(request, f"Success: {count} devices added!")
        except Exception as e: 
            messages.error(request, str(e))
        return redirect('bulk_upload')
    return render(request, 'bulk_upload.html', get_base_context())

@login_required(login_url='/login/')
def export_devices_view(request):
    if request.method == 'POST':
        prov_id, bts_id, dev_type = request.POST.get('province'), request.POST.get('bts'), request.POST.get('device_type')
        devices = Device.objects.all().select_related('bts', 'bts__province')
        if prov_id and prov_id != 'all': devices = devices.filter(bts__province_id=prov_id)
        if bts_id and bts_id != 'all': devices = devices.filter(bts_id=bts_id)
        if dev_type and dev_type != 'all': devices = devices.filter(device_type=dev_type)
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.append(['BTS Name', 'Province', 'Device Type', 'IP Address', 'MAC Address', 'Device Model', 'SSID', 'Frequency'])
        for d in devices: ws.append([d.bts.name, d.bts.province.name, d.get_device_type_display(), d.ip_address, d.mac_address, d.get_device_model_display(), d.ssid, d.frequency])
        response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        response['Content-Disposition'] = 'attachment; filename="Export.xlsx"'
        wb.save(response)
        return response
    context = get_base_context()
    context.update({'provinces': Province.objects.all(), 'btss': BTS.objects.all(), 'device_types': Device.DEVICE_TYPES})
    return render(request, 'export_filter.html', context)

@login_required(login_url='/login/')
def device_list(request):
    devices = Device.objects.select_related('bts', 'bts__province').all().order_by('-id')
    q, prov, dev = request.GET.get('search', ''), request.GET.get('province', ''), request.GET.get('device_type', '')
    if q: devices = devices.filter(Q(ip_address__icontains=q)|Q(mac_address__icontains=q)|Q(bts__name__icontains=q))
    if prov: devices = devices.filter(bts__province_id=prov)
    if dev: devices = devices.filter(device_type=dev)
    paginator = Paginator(devices, 20)
    try: page_obj = paginator.page(request.GET.get('page'))
    except: page_obj = paginator.page(1)
    context = get_base_context()
    context.update({'devices': page_obj, 'page_obj': page_obj, 'provinces': Province.objects.all()})
    return render(request, 'device_list.html', context)

@login_required(login_url='/login/')
def search_mac_view(request):
    result = None
    if request.method == 'POST':
        mac_query, prov_id, dev_type = request.POST.get('mac_address'), request.POST.get('province'), request.POST.get('device_type')
        if mac_query and prov_id and dev_type:
            try:
                prov = Province.objects.get(id=prov_id)
                devices = Device.objects.filter(bts__province=prov, device_type=dev_type)
                host_list = [dev.ip_address for dev in devices if dev.ip_address]
                if host_list:
                    u, p, po = (prov.mt_user, prov.mt_pass, prov.mt_port) if dev_type == 'mikrotik' else (prov.cisco_user, prov.cisco_pass, prov.cisco_port)
                    result = search_mac_in_network(host_list, dev_type, mac_query, u, p, po)
                else: result = {"status": "error", "message": "No devices found."}
            except Exception as e: result = {"status": "error", "message": str(e)}
    context = get_base_context()
    context.update({'provinces': Province.objects.all(), 'result': result})
    return render(request, 'search_mac.html', context)

@login_required(login_url='/login/')
def check_signal_view(request):
    results, searched_prov = None, None
    if request.method == 'POST':
        prov_id, bts_ids, site_ips = request.POST.get('province'), request.POST.getlist('bts'), request.POST.getlist('site')
        try: threshold = int(request.POST.get('threshold', '-75'))
        except: threshold = -75
        if prov_id:
            try:
                searched_prov = Province.objects.get(id=prov_id)
                if site_ips and any(ip.strip() for ip in site_ips):
                    valid_ips = [ip.strip() for ip in site_ips if ip.strip()]
                    devices = Device.objects.filter(ip_address__in=valid_ips, device_type='mikrotik')
                elif bts_ids and any(bts.strip() for bts in bts_ids):
                    valid_bts = [bts.strip() for bts in bts_ids if bts.strip()]
                    devices = Device.objects.filter(bts_id__in=valid_bts, device_type='mikrotik')
                else:
                    devices = Device.objects.filter(bts__province=searched_prov, device_type='mikrotik')

                results = []
                for dev in devices:
                    if dev.ip_address:
                        res = report_signal_strength(dev.ip_address, searched_prov.mt_user, searched_prov.mt_pass, searched_prov.mt_port, threshold)
                        res['bts_name'] = dev.bts.name
                        results.append(res)
            except Exception as e: results = [{"status": "error", "error": str(e)}]
    context = get_base_context()
    context.update({'provinces': Province.objects.all(), 'btss': BTS.objects.select_related('province').all(), 'results': results, 'searched_prov': searched_prov})
    return render(request, 'check_signal.html', context)

@login_required(login_url='/login/')
def wireless_clients_view(request):
    results, searched_prov = None, None
    if request.method == 'POST':
        prov_id, bts_ids, site_ips = request.POST.get('province'), request.POST.getlist('bts'), request.POST.getlist('site')
        if prov_id:
            try:
                searched_prov = Province.objects.get(id=prov_id)
                if site_ips and any(ip.strip() for ip in site_ips):
                    valid_ips = [ip.strip() for ip in site_ips if ip.strip()]
                    devices = Device.objects.filter(ip_address__in=valid_ips, device_type='mikrotik')
                elif bts_ids and any(bts.strip() for bts in bts_ids):
                    valid_bts = [bts.strip() for bts in bts_ids if bts.strip()]
                    devices = Device.objects.filter(bts_id__in=valid_bts, device_type='mikrotik')
                else:
                    devices = Device.objects.filter(bts__province=searched_prov, device_type='mikrotik')
                
                results = []
                for dev in devices:
                    if dev.ip_address:
                        res = report_customers(dev.ip_address, searched_prov.mt_user, searched_prov.mt_pass, searched_prov.mt_port)
                        res['bts_name'], res['ssid'] = dev.bts.name, dev.ssid
                        results.append(res)
            except Exception as e: results = [{"status": "error", "error": str(e)}]
    context = get_base_context()
    context.update({'provinces': Province.objects.all(), 'btss': BTS.objects.select_related('province').all(), 'sites': Device.objects.filter(device_type='mikrotik'), 'results': results, 'searched_prov': searched_prov})
    return render(request, 'wireless_clients.html', context)

@login_required(login_url='/login/')
def switch_report_view(request):
    results, searched_prov = None, None
    if request.method == 'POST':
        prov_id, bts_ids, site_ips = request.POST.get('province'), request.POST.getlist('bts'), request.POST.getlist('site')
        if prov_id:
            try:
                searched_prov = Province.objects.get(id=prov_id)
                if site_ips and any(ip.strip() for ip in site_ips):
                    valid_ips = [ip.strip() for ip in site_ips if ip.strip()]
                    devices = Device.objects.filter(ip_address__in=valid_ips, device_type='cisco')
                elif bts_ids and any(bts.strip() for bts in bts_ids):
                    valid_bts = [bts.strip() for bts in bts_ids if bts.strip()]
                    devices = Device.objects.filter(bts_id__in=valid_bts, device_type='cisco')
                else:
                    devices = Device.objects.filter(bts__province=searched_prov, device_type='cisco')
                
                results = []
                for dev in devices:
                    if dev.ip_address:
                        res = report_switch_web(dev.ip_address, searched_prov.cisco_user, searched_prov.cisco_pass, searched_prov.cisco_port)
                        res['bts_name'] = dev.bts.name
                        results.append(res)
            except Exception as e: results = [{"status": "error", "error": str(e)}]
    context = get_base_context()
    context.update({'provinces': Province.objects.all(), 'btss': BTS.objects.select_related('province').all(), 'sites': Device.objects.filter(device_type='cisco'), 'results': results, 'searched_prov': searched_prov})
    return render(request, 'switch_report.html', context)

@login_required(login_url='/login/')
def employee_panel_view(request):
    user_creds = UserProvinceCredential.objects.filter(user=request.user)
    creds_dict = {}
    for c in user_creds:
        creds_dict[c.province.id] = {
            's_pass': c.sender_pass or '',
            'r_pass': c.receiver_pass or ''
        }

    context = get_base_context()
    context.update({
        'target_ip': request.GET.get('target_ip'),
        'provinces': Province.objects.all(),
        'user_creds_json': json.dumps(creds_dict)
    })
    return render(request, 'employee_panel.html', context)

@login_required(login_url='/login/')
def update_profile(request):
    provinces = Province.objects.all()
    if request.method == 'POST':
        prov_id = request.POST.get('province_id')
        if prov_id:
            province = get_object_or_404(Province, id=prov_id)
            s_pass = request.POST.get('sender_password')
            r_pass = request.POST.get('receiver_password')
            cred, created = UserProvinceCredential.objects.get_or_create(user=request.user, province=province)
            cred.sender_pass = s_pass
            cred.receiver_pass = r_pass
            cred.save()
            messages.success(request, f"Credentials for {province.name} updated successfully.")
            return redirect('update_profile')
            
    user_creds = UserProvinceCredential.objects.filter(user=request.user)
    creds_dict = {}
    for c in user_creds:
        creds_dict[c.province.id] = {'s_pass': c.sender_pass or '', 'r_pass': c.receiver_pass or ''}

    return render(request, 'update_profile.html', {
        'provinces': provinces, 'creds_json': json.dumps(creds_dict)
    })

@login_required(login_url='/login/')
def smart_ping_and_log(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            ip_address = data.get('ip_address')
            province_id = data.get('province_id')
            device_type = data.get('device_type', 'unknown')

            if not ip_address:
                return JsonResponse({'status': 'error', 'message': 'IP address is required.'})

            param = '-n' if platform.system().lower() == 'windows' else '-c'
            command = ['ping', param, '1', '-W', '1', ip_address]
            
            try:
                output = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                is_online = (output.returncode == 0)
            except Exception:
                is_online = False

            province = Province.objects.filter(id=province_id).first() if province_id else None
            ConnectionLog.objects.create(
                user=request.user, province=province, ip_address=ip_address,
                device_type=device_type, is_online=is_online
            )
            return JsonResponse({'status': 'success', 'is_online': is_online})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)})
    return JsonResponse({'status': 'error', 'message': 'Invalid request method.'})

@login_required(login_url='/login/')
def live_map_view(request):
    bts_list = BTS.objects.exclude(latitude__isnull=True).exclude(longitude__isnull=True)
    active_links = NetworkLink.objects.filter(
        is_active=True, source_bts__latitude__isnull=False, source_bts__longitude__isnull=False,
        target_bts__latitude__isnull=False, target_bts__longitude__isnull=False
    ).select_related('source_bts', 'target_bts')
    
    context = get_base_context()
    context.update({ 'bts_list': bts_list, 'links': active_links })
    return render(request, 'live_map.html', context)

# ==========================================
# ⚙️ Map Management View (مبتنی بر IP مستقیم)
# ==========================================
@login_required(login_url='/login/')
def map_management_view(request):
    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'add_link':
            source_id = request.POST.get('source_bts')
            target_id = request.POST.get('target_bts')
            link_type = request.POST.get('link_type')
            capacity = request.POST.get('capacity_mbps', 1000)
            
            src_ip = request.POST.get('source_ip')
            src_interface = request.POST.get('source_interface')
            snmp_community = request.POST.get('snmp_community', 'public')
            
            tgt_ip = request.POST.get('target_ip')
            tgt_interface = request.POST.get('target_interface')
            tgt_snmp_community = request.POST.get('target_snmp_community', 'public')

            if source_id == target_id:
                messages.error(request, "Error: Source and Target BTS cannot be the same!")
            elif not source_id or not target_id:
                messages.error(request, "Please select both Source and Target BTS.")
            else:
                try:
                    NetworkLink.objects.create(
                        source_bts_id=source_id,
                        target_bts_id=target_id,
                        source_ip=src_ip,
                        source_interface=src_interface,
                        snmp_community=snmp_community,
                        target_ip=tgt_ip,
                        target_interface=tgt_interface,
                        target_snmp_community=tgt_snmp_community,
                        link_type=link_type,
                        capacity_mbps=capacity
                    )
                    messages.success(request, "Network link successfully created!")
                except Exception as e:
                    messages.error(request, f"Database Error: {str(e)}")
        
        elif action == 'edit_link':
            link_id = request.POST.get('link_id')
            try:
                link = NetworkLink.objects.get(id=link_id)
                link.link_type = request.POST.get('link_type')
                link.capacity_mbps = request.POST.get('capacity_mbps')
                if 'snmp_community' in request.POST:
                    link.snmp_community = request.POST.get('snmp_community')
                if 'target_snmp_community' in request.POST:
                    link.target_snmp_community = request.POST.get('target_snmp_community')
                link.save()
                messages.success(request, "Link updated successfully.")
            except Exception as e:
                messages.error(request, f"Error updating link: {str(e)}")

        elif action == 'delete_link':
            link_id = request.POST.get('link_id')
            try:
                NetworkLink.objects.get(id=link_id).delete()
                messages.success(request, "Link deleted successfully.")
            except:
                messages.error(request, "Error deleting the link.")
                
        return redirect('map_management')

    context = get_base_context()
    
    # تغییر اعمال شده برای نمایش تمامی استان‌ها (حتی استان‌های بدون دکل مثل بادغیس)
    context.update({
        'provinces': Province.objects.all().order_by('name'), 
        'btss': BTS.objects.select_related('province').all().order_by('province__name', 'name'),
        'links': NetworkLink.objects.select_related('source_bts', 'target_bts').all().order_by('-id'),
        'link_types': NetworkLink.LINK_TYPES
    })
    return render(request, 'map_management.html', context)


# ==========================================
# 📡 Fetch Interfaces via SNMP (آی‌پی مستقیم)
# ==========================================
@login_required(login_url='/login/')
def fetch_interfaces_view(request):
    ip_address = request.GET.get('ip')
    community = request.GET.get('community', 'public') 
    
    if not ip_address:
        return JsonResponse({'status': 'error', 'message': 'IP Address missing'})
    try:
        interfaces = get_device_interfaces(ip_address, community)
        
        if interfaces:
            return JsonResponse({'status': 'success', 'interfaces': interfaces})
        else:
            return JsonResponse({'status': 'error', 'message': 'No interfaces found or SNMP timeout.'})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)})