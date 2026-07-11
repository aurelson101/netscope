import re

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

def normalize_mac(value:str|None)->str|None:
    if not value:return None
    compact=re.sub(r"[^0-9A-Fa-f]","",value)
    if len(compact)!=12:return None
    return ":".join(compact[i:i+2] for i in range(0,12,2)).upper()

def is_private_mac(value:str|None)->bool:
    normalized=normalize_mac(value)
    return bool(normalized and int(normalized[:2],16)&2)
