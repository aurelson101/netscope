import re

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
