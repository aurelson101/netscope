from datetime import datetime, timedelta, timezone
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from app.discovery.snmp.parser import mac_from_oid_suffix, normalize_mac, parse_inet_routes, parse_ip_neighbors, parse_ipv4_routes, parse_neighbors, snmp_integer
from app.models import ArpEntry, Asset, AssetAddress, AssetIdentifier, InterfaceMetric, NetworkDevice, PortMacEntry, RouteEntry, SwitchPort, TopologyLink, TopologyNode, Vlan
from app.services.alerts import open_alert,resolve_alert


def _index(oid:str)->int|None:
    try:return int(oid.rsplit(".",1)[1])
    except ValueError:return None

def counter_rate(current:int|None,previous:int|None,seconds:float)->float|None:
    if current is None or previous is None or seconds<=0 or current<previous:return None
    return (current-previous)*8/seconds


async def ingest_infrastructure(db:AsyncSession,asset:Asset,ip:str,sections:dict,vrf_id:str|None=None):
    system={x["oid"]:x["value"] for x in sections.get("system",[])}
    device=(await db.execute(select(NetworkDevice).where(NetworkDevice.asset_id==asset.id))).scalar_one_or_none()
    if not device:
        device=NetworkDevice(asset_id=asset.id);db.add(device);await db.flush()
    device.management_ip=ip;device.last_polled=datetime.now(timezone.utc)
    for oid,value in system.items():
        if oid.endswith(".1.0"):device.sys_descr=value
        elif oid.endswith(".2.0"):device.sys_object_id=value
        elif oid.endswith(".3.0"):device.uptime_ticks=snmp_integer(value)
        elif oid.endswith(".5.0"):device.sys_name=value
    ports={}
    interface_rows=sections.get("interfaces",[])+sections.get("if_names",[])
    for row in interface_rows:
        idx=_index(row["oid"])
        if idx is None:continue
        port=ports.get(idx) or (await db.execute(select(SwitchPort).where(SwitchPort.network_device_id==device.id,SwitchPort.if_index==idx))).scalar_one_or_none()
        if not port:port=SwitchPort(network_device_id=device.id,if_index=idx);db.add(port)
        ports[idx]=port
        oid=row["oid"]
        if ".2.2.1.2." in oid:port.description=row["value"]
        elif ".31.1.1.1.1." in oid:port.name=row["value"]
        elif ".2.2.1.7." in oid:port.admin_status=row["value"]
        elif ".2.2.1.8." in oid:port.oper_status=row["value"]
        elif ".2.2.1.6." in oid:port.mac_address=normalize_mac(row["value"])
    await db.flush()
    collected_at=datetime.now(timezone.utc)
    counters={}
    for row in interface_rows:
        idx=_index(row["oid"]);value=snmp_integer(row["value"])
        if idx is None or value is None:continue
        item=counters.setdefault(idx,{})
        oid=row["oid"]
        if ".31.1.1.1.6." in oid:item["in_octets"]=value
        elif ".31.1.1.1.10." in oid:item["out_octets"]=value
        elif ".31.1.1.1.15." in oid and value>0:item["speed_bps"]=value*1_000_000
        elif ".2.2.1.5." in oid:item.setdefault("speed_bps",value)
        elif ".2.2.1.10." in oid:item.setdefault("in_octets",value)
        elif ".2.2.1.14." in oid:item["in_errors"]=value
        elif ".2.2.1.16." in oid:item.setdefault("out_octets",value)
        elif ".2.2.1.20." in oid:item["out_errors"]=value
    for idx,values in counters.items():
        port=ports.get(idx)
        if not port:continue
        previous=(await db.execute(select(InterfaceMetric).where(InterfaceMetric.switch_port_id==port.id).order_by(InterfaceMetric.collected_at.desc()).limit(1))).scalar_one_or_none()
        seconds=(collected_at-(previous.collected_at if previous and previous.collected_at.tzinfo else previous.collected_at.replace(tzinfo=timezone.utc))).total_seconds() if previous else 0
        in_bps=counter_rate(values.get("in_octets"),previous.in_octets if previous else None,seconds);out_bps=counter_rate(values.get("out_octets"),previous.out_octets if previous else None,seconds);speed=values.get("speed_bps")
        in_util=min(in_bps*100/speed,100) if in_bps is not None and speed else None;out_util=min(out_bps*100/speed,100) if out_bps is not None and speed else None
        db.add(InterfaceMetric(switch_port_id=port.id,collected_at=collected_at,speed_bps=speed,in_octets=values.get("in_octets"),out_octets=values.get("out_octets"),in_errors=values.get("in_errors"),out_errors=values.get("out_errors"),in_bps=in_bps,out_bps=out_bps,in_utilization=in_util,out_utilization=out_util))
        fingerprint=f"interface_saturation:{port.id}";current_util=max(x for x in (in_util,out_util) if x is not None) if in_util is not None or out_util is not None else None;previous_util=max(x for x in (previous.in_utilization,previous.out_utilization) if x is not None) if previous and (previous.in_utilization is not None or previous.out_utilization is not None) else None
        if current_util is not None and previous_util is not None and current_util>=90 and previous_util>=90:await open_alert(db,fingerprint=fingerprint,kind="interface_saturation",severity="warning",title="Interface réseau saturée",message=f"L'interface {port.name or port.description or idx} de {device.sys_name or ip} dépasse 90 % sur deux collectes.",asset_id=asset.id,details={"port_id":port.id,"in_utilization":in_util,"out_utilization":out_util})
        elif current_util is not None and current_util<80:await resolve_alert(db,fingerprint)
    for row in sections.get("vlans",[]):
        if ".1.4.3.1.1." not in row["oid"]:continue
        vlan_id=_index(row["oid"])
        if vlan_id is None:continue
        vlan=(await db.execute(select(Vlan).where(Vlan.site_id==asset.site_id,Vlan.vlan_id==vlan_id))).scalar_one_or_none()
        if not vlan:db.add(Vlan(site_id=asset.site_id,vlan_id=vlan_id,name=row["value"]))
        else:vlan.name=row["value"];vlan.last_seen=datetime.now(timezone.utc)
    arp_rows=sections.get("arp",[])
    arp_macs={}
    for row in arp_rows:
        if ".4.22.1.2." in row["oid"]:
            suffix=row["oid"].split(".4.22.1.2.",1)[1].split(".");
            if len(suffix)>=5:arp_macs[".".join(suffix[1:5])]=(_index(row["oid"]),normalize_mac(row["value"]))
    for address,(if_index,mac) in arp_macs.items():
        if not mac:continue
        entry=(await db.execute(select(ArpEntry).where(ArpEntry.network_device_id==device.id,ArpEntry.ip_address==address,ArpEntry.mac_address==mac))).scalar_one_or_none()
        if not entry:db.add(ArpEntry(network_device_id=device.id,ip_address=address,mac_address=mac,if_index=if_index))
        else:entry.if_index=if_index;entry.last_seen=datetime.now(timezone.utc)
    for neighbor in parse_ip_neighbors(sections.get("neighbors",[])):
        entry=(await db.execute(select(ArpEntry).where(ArpEntry.network_device_id==device.id,ArpEntry.ip_address==neighbor["ip_address"],ArpEntry.mac_address==neighbor["mac_address"]))).scalar_one_or_none()
        if not entry:db.add(ArpEntry(network_device_id=device.id,**neighbor))
        else:entry.if_index=neighbor["if_index"];entry.last_seen=datetime.now(timezone.utc)
    routes=parse_ipv4_routes(sections.get("routes_v4",[]))+parse_inet_routes(sections.get("routes_inet",[]));seen_routes=set()
    for route in routes:
        key=(route["prefix"],route.get("next_hop"),route["protocol"]);seen_routes.add(key)
        route_scope=RouteEntry.vrf_id.is_(None) if vrf_id is None else RouteEntry.vrf_id==vrf_id
        existing=(await db.execute(select(RouteEntry).where(RouteEntry.network_device_id==device.id,route_scope,RouteEntry.prefix==route["prefix"],RouteEntry.next_hop==route.get("next_hop"),RouteEntry.protocol==route["protocol"]))).scalar_one_or_none()
        if not existing:db.add(RouteEntry(network_device_id=device.id,vrf_id=vrf_id,**route))
        else:existing.if_index=route.get("if_index");existing.metric=route.get("metric");existing.active=True;existing.last_seen=datetime.now(timezone.utc)
    route_errors=set(sections.get("_errors",{}))&{"routes_v4","routes_inet"}
    if not route_errors:
        route_scope=RouteEntry.vrf_id.is_(None) if vrf_id is None else RouteEntry.vrf_id==vrf_id
        for stale_route in (await db.execute(select(RouteEntry).where(RouteEntry.network_device_id==device.id,route_scope,RouteEntry.active.is_(True)))).scalars():
            if (stale_route.prefix,stale_route.next_hop,stale_route.protocol) not in seen_routes:stale_route.active=False
    bridge_map={_index(x["oid"]):int(x["value"]) for x in sections.get("bridge_ports",[]) if x["value"].isdigit()}
    fdb_ports={mac_from_oid_suffix(x["oid"]):bridge_map.get(int(x["value"]),int(x["value"])) for x in sections.get("fdb",[]) if ".17.4.3.1.2." in x["oid"] and mac_from_oid_suffix(x["oid"]) and x["value"].isdigit()}
    for mac,bridge_port in fdb_ports.items():
        port=ports.get(bridge_port)
        if not port:continue
        linked=(await db.execute(select(Asset).join(AssetIdentifier).where(AssetIdentifier.kind=="mac",AssetIdentifier.value==mac))).scalar_one_or_none()
        entry=(await db.execute(select(PortMacEntry).where(PortMacEntry.switch_port_id==port.id,PortMacEntry.mac_address==mac,PortMacEntry.vlan_id.is_(None)))).scalar_one_or_none()
        if not entry:db.add(PortMacEntry(switch_port_id=port.id,mac_address=mac,asset_id=linked.id if linked else None))
    local_node=(await db.execute(select(TopologyNode).where(TopologyNode.asset_id==asset.id))).scalar_one_or_none()
    if not local_node:local_node=TopologyNode(asset_id=asset.id,label=asset.hostname or ip,kind=asset.device_type);db.add(local_node)
    await db.flush()
    for neighbor in parse_neighbors(sections):
        protocol=neighbor["protocol"];label=neighbor["label"];local_port=ports.get(neighbor["local_if_index"]);remote_port=neighbor["remote_port"]
        remote=(await db.execute(select(TopologyNode).where(func.lower(TopologyNode.label)==label.casefold()))).scalar_one_or_none()
        if not remote:remote=TopologyNode(label=label,kind="network");db.add(remote);await db.flush()
        source_port=(local_port.name or local_port.description or str(neighbor["local_if_index"])) if local_port else None
        link=(await db.execute(select(TopologyLink).where(TopologyLink.source_node_id==local_node.id,TopologyLink.target_node_id==remote.id,TopologyLink.source==protocol,TopologyLink.source_port==source_port))).scalar_one_or_none()
        if not link:db.add(TopologyLink(source_node_id=local_node.id,target_node_id=remote.id,source_port=source_port,target_port=remote_port,source=protocol,confidence=0.98))
        else:link.source_port=source_port;link.target_port=remote_port;link.last_seen=datetime.now(timezone.utc);link.confidence=0.98
    await db.execute(delete(InterfaceMetric).where(InterfaceMetric.collected_at<datetime.now(timezone.utc)-timedelta(days=90)))
    await db.commit()
