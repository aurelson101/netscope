import re
import csv
from functools import lru_cache
from pathlib import Path

MOBILE_VENDORS=("Apple","Samsung","Google","Xiaomi","Redmi","Poco","Huawei","Honor","Oppo","OnePlus","Realme","Vivo","Motorola","Lenovo","Nokia","HMD","Sony","Asus","Nothing","Fairphone","ZTE","Nubia","TCL","Alcatel","Tecno","Infinix","Itel","Meizu","Sharp","Kyocera","LG","HTC","BlackBerry","Microsoft","Cat","Doogee","Ulefone","Oukitel","Wiko")
ALIASES={"APPLE INC":"Apple","APPLE COMPUTER":"Apple","SAMSUNG ELECTRONICS":"Samsung","SAMSUNG ELEC":"Samsung","GOOGLE INC":"Google","GOOGLE LLC":"Google","XIAOMI COMMUNICATIONS":"Xiaomi","BEIJING XIAOMI":"Xiaomi","HUAWEI TECHNOLOGIES":"Huawei","HONOR DEVICE":"Honor","GUANGDONG OPPO":"Oppo","ONEPLUS TECHNOLOGY":"OnePlus","REALME MOBILE":"Realme","VIVO MOBILE":"Vivo","MOTOROLA MOBILITY":"Motorola","HMD GLOBAL":"HMD","SONY MOBILE":"Sony","NOTHING TECHNOLOGY":"Nothing","FAIRPHONE B.V":"Fairphone","ZTE CORPORATION":"ZTE","TCL COMMUNICATION":"TCL","TCT MOBILE":"Alcatel","TECNO MOBILE":"Tecno","INFINIX MOBILITY":"Infinix","SHENZHEN TRANSSION":"Tecno","LG ELECTRONICS":"LG","HTC CORPORATION":"HTC","ASUSTEK COMPUTER":"Asus"}

def normalize_vendor(value:str|None)->str|None:
    if not value:return None
    upper=re.sub(r"[.,®™]","",value).strip().upper()
    for alias,canonical in ALIASES.items():
        if alias in upper:return canonical
    for canonical in MOBILE_VENDORS:
        if re.search(rf"\b{re.escape(canonical.upper())}\b",upper):return canonical
    return value.strip()

def infer_mobile_identity(hostname:str|None=None,model:str|None=None,operating_system:str|None=None)->dict:
    text=" ".join(x for x in (hostname,model,operating_system) if x).upper()
    if any(marker in text for marker in ("IPHONE","IPAD","APPLE IOS","IOS ")):
        return {"manufacturer":"Apple","device_type":"tablet" if "IPAD" in text else "phone","operating_system":"Apple iOS"}
    if re.search(r"\bPIXEL(?:[- _]?\d|[- _]?PRO|[- _]?FOLD|[- _]?XL|\b)",text):
        return {"manufacturer":"Google","device_type":"phone","operating_system":"Android"}
    if "ANDROID" in text:
        return {"device_type":"phone","operating_system":"Android"}
    return {}

def infer_device_type(hostname:str|None=None,manufacturer:str|None=None,model:str|None=None,operating_system:str|None=None,ports:set[int]|None=None)->str|None:
    text=" ".join(x for x in (hostname,manufacturer,model,operating_system) if x).upper()
    ports=ports or set()
    if any(x in text for x in ("GATEWAY","ROUTER","ROUTEROS","FIREWALL","SAGEMCOM","OPENWRT","EDGEOS")):
        return "router"
    if any(x in text for x in ("SWITCH","BRIDGE","IOS XE","JUNOS","ARISTA")):
        return "switch"
    if any(x in text for x in ("ACCESS POINT","WIRELESS","UNIFI","UBIQUITI AP")):
        return "access_point"
    if any(x in text for x in ("PRINTER","LASERJET","JETDIRECT")) or 9100 in ports:
        return "printer"
    if any(x in text for x in ("PHONE","IPHONE","ANDROID","PIXEL")):
        return "phone"
    if any(x in text for x in ("WINDOWS","LINUX","MACOS","DESKTOP","LAPTOP","WORKSTATION","AUREL-","PC-")) or ports & {135,139,445,3389}:
        return "workstation"
    return None

def normalize_mac(value:str|None)->str|None:
    if not value:return None
    compact=re.sub(r"[^0-9A-Fa-f]","",value)
    if len(compact)!=12:return None
    return ":".join(compact[i:i+2] for i in range(0,12,2)).upper()

def is_private_mac(value:str|None)->bool:
    normalized=normalize_mac(value)
    return bool(normalized and int(normalized[:2],16)&2)

@lru_cache
def offline_oui()->dict[str,str]:
    """Load the local catalog, enriched with Nmap's maintained MAC prefixes.

    The bundled CSV remains the first source (it may contain local overrides),
    while the system Nmap database provides thousands of additional vendors.
    """
    result: dict[str, str] = {}
    path=Path(__file__).parents[3]/"data"/"oui"/"oui.csv"
    if not path.exists():path=Path(__file__).parents[1]/"data"/"oui.csv"
    if path.exists():
        with path.open(encoding="utf-8") as handle:
            result.update({row["prefix"].replace(":", "").upper():row["vendor"].strip()
                           for row in csv.DictReader(handle)
                           if row.get("prefix") and row.get("vendor")})

    # Debian/Ubuntu and the official Nmap image install this at this path.
    nmap_path = Path("/usr/share/nmap/nmap-mac-prefixes")
    if nmap_path.exists():
        with nmap_path.open(encoding="utf-8", errors="replace") as handle:
            for line in handle:
                line=line.strip()
                if not line or line.startswith("#") or " " not in line:
                    continue
                prefix, vendor = line.split(None, 1)
                prefix=prefix.replace(":", "").upper()
                if len(prefix) >= 6 and vendor.strip():
                    result.setdefault(prefix[:6], vendor.strip())
    return result

def vendor_from_mac(value:str|None)->str|None:
    mac=normalize_mac(value)
    if not mac or is_private_mac(mac):return None
    return normalize_vendor(offline_oui().get(mac.replace(":","")[:6]))
