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
