import asyncio
from pysnmp.hlapi.v3arch.asyncio import (
    SnmpEngine, CommunityData, UdpTransportTarget, ContextData,
    ObjectType, ObjectIdentity, walk_cmd, get_cmd
)

async def _fetch_interfaces_async(ip, community):
    """
    ???? ???? ? ???????? ???? ????? ???????
    """
    snmpEngine = SnmpEngine()
    interfaces = []
    port = 161
    
    # ????? ?????: ???? ??? ????? ?? ??? create ? await
    transport_target = await UdpTransportTarget.create((ip, port), timeout=5, retries=2)
    
    # ?. ?????? ??? ???????
    async for errorIndication, errorStatus, errorIndex, varBinds in walk_cmd(
        snmpEngine,
        CommunityData(community, mpModel=1),
        transport_target,
        ContextData(),
        ObjectType(ObjectIdentity('1.3.6.1.2.1.2.2.1.2')),
        lexicographicMode=False
    ):
        if errorIndication:
            raise Exception(f"Network Error: {errorIndication}")
        if errorStatus:
            raise Exception(f"SNMP Error: {errorStatus.prettyPrint()}")
            
        for varBind in varBinds:
            oid = varBind[0].prettyPrint()
            idx = oid.split('.')[-1]
            name = str(varBind[1])
            interfaces.append({"index": idx, "name": name})

    if not interfaces:
        raise Exception("No interfaces found. Check SNMP community and IP.")

    # ?. ?????? ???? ???????
    speeds = {}
    async for errorIndication, errorStatus, errorIndex, varBinds in walk_cmd(
        snmpEngine,
        CommunityData(community, mpModel=1),
        transport_target,
        ContextData(),
        ObjectType(ObjectIdentity('1.3.6.1.2.1.2.2.1.5')),
        lexicographicMode=False
    ):
        if errorIndication or errorStatus:
            break
        for varBind in varBinds:
            oid = varBind[0].prettyPrint()
            idx = oid.split('.')[-1]
            try:
                speeds[idx] = int(varBind[1]) // 1000000
            except:
                speeds[idx] = 1000

    # ????? ??? ? ????
    result = []
    for iface in interfaces:
        idx = iface['index']
        result.append({"name": iface['name'], "speed": speeds.get(idx, 1000)})
        
    return result


def get_device_interfaces(ip, community):
    """
    ????? ???? ???????? ?? ???? ?????? ????
    """
    return asyncio.run(_fetch_interfaces_async(ip, community))


async def _get_traffic_async(ip, community, interface_name):
    """
    ????? ?????? ???? ???? ???
    """
    snmpEngine = SnmpEngine()
    port = 161
    if_index = None
    
    # ????? ?????: ???? ??? ????? ?? ??? create ? await
    transport_target = await UdpTransportTarget.create((ip, port), timeout=5, retries=2)
    
    # ???? ???? ????? Index ????
    async for errorIndication, errorStatus, errorIndex, varBinds in walk_cmd(
        snmpEngine,
        CommunityData(community, mpModel=1),
        transport_target,
        ContextData(),
        ObjectType(ObjectIdentity('1.3.6.1.2.1.2.2.1.2')),
        lexicographicMode=False
    ):
        if errorIndication or errorStatus:
            break
        for varBind in varBinds:
            oid = varBind[0].prettyPrint()
            value = str(varBind[1])
            if value == interface_name:
                if_index = oid.split('.')[-1]
                break
        if if_index:
            break

    if not if_index:
        return None, None

    # ?????? ????? 64 ???? ??????
    in_oid = ObjectType(ObjectIdentity(f'1.3.6.1.2.1.31.1.1.1.6.{if_index}'))
    out_oid = ObjectType(ObjectIdentity(f'1.3.6.1.2.1.31.1.1.1.10.{if_index}'))

    errorIndication, errorStatus, errorIndex, varBinds = await get_cmd(
        snmpEngine,
        CommunityData(community, mpModel=1),
        transport_target,
        ContextData(),
        in_oid, out_oid
    )

    if errorIndication or errorStatus:
        return None, None

    rx_bytes = int(varBinds[0][1])
    tx_bytes = int(varBinds[1][1])
    
    return rx_bytes, tx_bytes


def get_snmp_traffic(ip, community, interface_name):
    """
    ????? ???? ????? ??????
    """
    return asyncio.run(_get_traffic_async(ip, community, interface_name))