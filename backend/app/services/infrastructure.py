from datetime import datetime, timezone
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.discovery.snmp.parser import mac_from_oid_suffix, normalize_mac
from app.models import ArpEntry, Asset, AssetAddress, AssetIdentifier, NetworkDevice, PortMacEntry, SwitchPort, TopologyLink, TopologyNode, Vlan


def _index(oid:str)->int|None:
    try:return int(oid.rsplit(".",1)[1])
    except ValueError:return None


async def ingest_infrastructure(db:AsyncSession,asset:Asset,ip:str,sections:dict):
    system={x["oid"]:x["value"] for x in sections.get("system",[])}
    device=(await db.execute(select(NetworkDevice).where(NetworkDevice.asset_id==asset.id))).scalar_one_or_none()
    if not device:
        device=NetworkDevice(asset_id=asset.id);db.add(device);await db.flush()
    device.management_ip=ip;device.last_polled=datetime.now(timezone.utc)
    for oid,value in system.items():
        if oid.endswith(".1.0"):device.sys_descr=value
        elif oid.endswith(".2.0"):device.sys_object_id=value
        elif oid.endswith(".3.0"):
            try:device.uptime_ticks=int(''.join(x for x in value if x.isdigit()))
            except ValueError:pass
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
    neighbor_rows=[]
    for protocol in ("lldp","cdp"):
        for row in sections.get(protocol,[]):
            oid=row["oid"]
            is_name=(protocol=="lldp" and (".1.4.1.1.9." in oid or ".1.4.1.1.5." in oid)) or (protocol=="cdp" and ".1.2.1.1.6." in oid)
            if is_name and row["value"]:neighbor_rows.append((protocol,row["value"],oid.rsplit(".",1)[-1]))
    for protocol,label,remote_port in neighbor_rows:
        remote=(await db.execute(select(TopologyNode).where(TopologyNode.label==label))).scalar_one_or_none()
        if not remote:remote=TopologyNode(label=label,kind="network");db.add(remote);await db.flush()
        link=(await db.execute(select(TopologyLink).where(TopologyLink.source_node_id==local_node.id,TopologyLink.target_node_id==remote.id,TopologyLink.source==protocol))).scalar_one_or_none()
        if not link:db.add(TopologyLink(source_node_id=local_node.id,target_node_id=remote.id,target_port=remote_port,source=protocol,confidence=0.95))
    await db.commit()
