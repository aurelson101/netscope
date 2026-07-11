import xml.etree.ElementTree as ET
from app.discovery.base import DiscoveryResult
from app.services.vendors import normalize_mac


def parse_nmap_xml(xml: str) -> list[DiscoveryResult]:
    root = ET.fromstring(xml)
    results: list[DiscoveryResult] = []
    for host in root.findall("host"):
        status = host.find("status")
        addresses = {a.get("addrtype", ""): a.get("addr", "") for a in host.findall("address")}
        ip = addresses.get("ipv4") or addresses.get("ipv6")
        if not ip: continue
        facts = [{"field":"status", "value": status.get("state", "unknown") if status is not None else "unknown", "confidence":1.0}]
        for kind, value in addresses.items():
            if kind in ("ipv4", "ipv6"): facts.append({"field":"ip", "value":value, "confidence":1.0})
            if kind == "mac": facts.append({"field":"mac", "value":normalize_mac(value), "confidence":1.0})
        mac_node = next((a for a in host.findall("address") if a.get("addrtype") == "mac"), None)
        if mac_node is not None and mac_node.get("vendor"): facts.append({"field":"manufacturer", "value":mac_node.get("vendor"), "confidence":0.8})
        hostname = host.find("hostnames/hostname")
        if hostname is not None: facts.append({"field":"hostname", "value":hostname.get("name"), "confidence":0.8})
        osmatch = host.find("os/osmatch")
        if osmatch is not None:
            facts.append({"field":"operating_system", "value":osmatch.get("name"), "confidence":float(osmatch.get("accuracy", "0"))/100})
            osclass = osmatch.find("osclass")
            if osclass is not None and osclass.get("type"): facts.append({"field":"device_type", "value":osclass.get("type"), "confidence":float(osclass.get("accuracy", "0"))/100})
        services = []
        for port in host.findall("ports/port"):
            state = port.find("state")
            if state is None or state.get("state") != "open": continue
            service = port.find("service")
            item = {"protocol":port.get("protocol"), "port":int(port.get("portid", "0")), "name":service.get("name") if service is not None else None, "product":service.get("product") if service is not None else None, "version":service.get("version") if service is not None else None}
            services.append(item); facts.append({"field":"service", "value":item, "confidence":0.9})
            for script in port.findall("script"):
                output=script.get("output","")
                facts.append({"field":f"nmap_script_{script.get('id','unknown')}","value":output,"confidence":0.85})
                if script.get("id")=="smb-os-discovery":
                    for line in output.splitlines():
                        if "Computer name:" in line:facts.append({"field":"hostname","value":line.split(":",1)[1].strip(),"confidence":0.95})
                        if "OS:" in line:facts.append({"field":"operating_system","value":line.split(":",1)[1].strip(),"confidence":0.92})
        cpes=[x.text for x in host.findall(".//cpe") if x.text]
        for cpe in cpes:facts.append({"field":"cpe","value":cpe,"confidence":0.9})
        results.append(DiscoveryResult("nmap", ip, {"addresses":addresses, "services":services, "xml_host":ET.tostring(host, encoding="unicode")}, facts))
    return results
