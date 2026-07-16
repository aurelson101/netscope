import ipaddress,re

OID_LINE = re.compile(r"^(?P<oid>[^ ]+)\s+=\s+(?P<type>[^:]+):\s*(?P<value>.*)$")


def parse_walk(text: str) -> list[dict]:
    rows=[]
    for line in text.splitlines():
        match=OID_LINE.match(line.strip())
        if match:
            row=match.groupdict(); row["value"]=row["value"].strip('"'); rows.append(row)
    return rows


def mac_from_oid_suffix(oid: str) -> str | None:
    parts=oid.rsplit(".",6)[-6:]
    if len(parts)!=6 or not all(x.isdigit() and 0<=int(x)<=255 for x in parts): return None
    return ":".join(f"{int(x):02X}" for x in parts)


def normalize_mac(value: str) -> str | None:
    raw=re.sub(r"[^0-9A-Fa-f]","",value)
    if len(raw)!=12:return None
    return ":".join(raw[i:i+2].upper() for i in range(0,12,2))

def snmp_integer(value:str)->int|None:
    parenthesized=re.search(r"\((\d+)\)",value)
    if parenthesized:return int(parenthesized.group(1))
    match=re.search(r"-?\d+",value.replace(",",""))
    return int(match.group()) if match else None

def parse_neighbors(sections:dict)->list[dict]:
    neighbors=[]
    for protocol,rows,name_marker,port_marker in (("lldp",sections.get("lldp",[]),".1.4.1.1.9.",".1.4.1.1.7."),("cdp",sections.get("cdp",[]),".1.2.1.1.6.",".1.2.1.1.7.")):
        names={};ports={};local_indexes={}
        for row in rows:
            oid=row["oid"];marker=name_marker if name_marker in oid else port_marker if port_marker in oid else None
            if not marker:continue
            suffix=oid.split(marker,1)[1];parts=suffix.split(".");key=suffix
            if protocol=="lldp" and len(parts)>=3:local_indexes[key]=int(parts[-2]) if parts[-2].isdigit() else None
            elif protocol=="cdp" and parts:local_indexes[key]=int(parts[0]) if parts[0].isdigit() else None
            if marker==name_marker:names[key]=row["value"]
            else:ports[key]=row["value"]
        for key,label in names.items():
            if label:neighbors.append({"protocol":protocol,"label":label,"local_if_index":local_indexes.get(key),"remote_port":ports.get(key)})
    return neighbors

def _oid_bytes(parts:list[str])->bytes|None:
    if not parts or not all(x.isdigit() and 0<=int(x)<=255 for x in parts):return None
    return bytes(int(x) for x in parts)

def parse_ip_neighbors(rows:list[dict])->list[dict]:
    result=[]
    for row in rows:
        marker=".4.35.1.4."
        if marker not in row["oid"]:continue
        parts=row["oid"].split(marker,1)[1].split(".")
        if len(parts)<5 or not parts[0].isdigit() or not parts[1].isdigit():continue
        if_index=int(parts[0]);address_type=int(parts[1]);expected=4 if address_type==1 else 16 if address_type==2 else 0;declared=int(parts[2]) if parts[2].isdigit() else 0
        length=declared if declared==expected else expected;start=3 if declared==expected else 2
        raw=_oid_bytes(parts[start:start+length])
        mac=normalize_mac(row["value"])
        if raw and len(raw)==length and mac:result.append({"if_index":if_index,"ip_address":str(ipaddress.ip_address(raw)),"mac_address":mac})
    return result

ROUTE_PROTOCOLS={1:"other",2:"local",3:"netmgmt",4:"icmp",8:"rip",13:"ospf",14:"bgp",15:"idrp",16:"isis"}

def parse_ipv4_routes(rows:list[dict])->list[dict]:
    grouped={}
    markers={1:"prefix",2:"mask",4:"next_hop",5:"if_index",7:"protocol",11:"metric"}
    for row in rows:
        matched=next(((column,f".4.24.4.1.{column}.") for column in markers if f".4.24.4.1.{column}." in row["oid"]),None)
        if not matched:continue
        column,marker=matched;suffix=row["oid"].split(marker,1)[1];item=grouped.setdefault(suffix,{})
        value=row["value"]
        if column in (5,7,11):item[markers[column]]=snmp_integer(value)
        else:
            match=re.search(r"(?:\d{1,3}\.){3}\d{1,3}",value);item[markers[column]]=match.group() if match else value
    result=[]
    for item in grouped.values():
        try:prefix=str(ipaddress.ip_network(f"{item['prefix']}/{item['mask']}",strict=False))
        except (KeyError,ValueError):continue
        result.append({"prefix":prefix,"next_hop":item.get("next_hop"),"if_index":item.get("if_index"),"protocol":ROUTE_PROTOCOLS.get(item.get("protocol"),str(item.get("protocol") or "unknown")),"metric":item.get("metric")})
    return result

def parse_inet_routes(rows:list[dict])->list[dict]:
    result=[]
    for row in rows:
        marker=".4.24.7.1.7."
        if marker not in row["oid"]:continue
        parts=row["oid"].split(marker,1)[1].split(".")
        if len(parts)<4 or not parts[0].isdigit():continue
        address_type=int(parts[0]);expected=4 if address_type==1 else 16 if address_type==2 else 0;declared=int(parts[1]) if len(parts)>1 and parts[1].isdigit() else 0
        length=declared if declared==expected else expected;start=2 if declared==expected else 1
        raw=_oid_bytes(parts[start:start+length]);position=start+length
        if not raw or len(parts)<=position or not parts[position].isdigit():continue
        prefix_length=int(parts[position])
        try:prefix=str(ipaddress.ip_network(f"{ipaddress.ip_address(raw)}/{prefix_length}",strict=False))
        except ValueError:continue
        result.append({"prefix":prefix,"next_hop":None,"if_index":snmp_integer(row["value"]),"protocol":"inetCidrRoute","metric":None})
    return result
