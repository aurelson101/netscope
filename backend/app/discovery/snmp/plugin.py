import asyncio
from app.discovery.base import DiscoveryPlugin, DiscoveryResult
from app.discovery.snmp.parser import parse_walk

OIDS={
 "system":"1.3.6.1.2.1.1", "interfaces":"1.3.6.1.2.1.2.2.1",
 "if_names":"1.3.6.1.2.1.31.1.1.1", "arp":"1.3.6.1.2.1.4.22.1",
 "neighbors":"1.3.6.1.2.1.4.35.1", "routes_v4":"1.3.6.1.2.1.4.24.4.1",
 "routes_inet":"1.3.6.1.2.1.4.24.7.1",
 "fdb":"1.3.6.1.2.1.17.4.3.1", "vlans":"1.3.6.1.2.1.17.7.1.4.3.1",
 "bridge_ports":"1.3.6.1.2.1.17.1.4.1.2",
 "lldp":"1.0.8802.1.1.2.1.4", "cdp":"1.3.6.1.4.1.9.9.23.1.2.1.1",
}
ENTERPRISE_VENDORS={"9":"Cisco","11":"HPE","2636":"Juniper Networks","12356":"Fortinet","25461":"Palo Alto Networks","41112":"Ubiquiti","14988":"MikroTik","2011":"Huawei","674":"Dell","30065":"Arista"}


class SnmpPlugin(DiscoveryPlugin):
    name="snmp"
    async def discover(self,target:str,options:dict):
        credential=options.get("credential") or {}
        version=str(credential.get("version","")).lower()
        timeout=["-t",str(options.get("timeout",3)),"-r",str(options.get("retries",1))]
        if version=="3":
            user=credential.get("username")
            if not user:raise ValueError("Nom d'utilisateur SNMPv3 manquant")
            base=["snmpbulkwalk","-v3","-l",credential.get("security_level","authPriv"),"-u",user,*timeout]
            if credential.get("auth_password"):base += ["-a",credential.get("auth_protocol","SHA"),"-A",credential["auth_password"]]
            if credential.get("privacy_password"):base += ["-x",credential.get("privacy_protocol","AES"),"-X",credential["privacy_password"]]
        elif version in ("2","2c","v2c"):
            if not credential.get("community"):raise ValueError("Communauté SNMPv2c manquante")
            base=["snmpbulkwalk","-v2c","-c",credential["community"],*timeout]
        else:raise ValueError("Version SNMP non prise en charge (utilisez 3 ou 2c)")
        sections={};section_errors={}
        for name,oid in OIDS.items():
            proc=await asyncio.create_subprocess_exec(*base,target,oid,stdout=asyncio.subprocess.PIPE,stderr=asyncio.subprocess.PIPE)
            try:stdout,stderr=await asyncio.wait_for(proc.communicate(),timeout=options.get("section_timeout",30))
            except TimeoutError:
                proc.kill();await proc.communicate()
                if name=="system":raise RuntimeError("La collecte SNMP système a dépassé le délai autorisé") from None
                sections[name]=[];section_errors[name]="timeout";continue
            sections[name]=parse_walk(stdout.decode(errors="replace"))
            if name=="system" and proc.returncode!=0: raise RuntimeError(stderr.decode(errors="replace")[:500])
            if proc.returncode!=0:section_errors[name]=stderr.decode(errors="replace")[:500]
        sections["_errors"]=section_errors
        facts=[{"field":"ip","value":target,"confidence":1.0},{"field":"status","value":"online","confidence":1.0}]
        system={row["oid"]:row["value"] for row in sections["system"]}
        for oid,value in system.items():
            if oid.endswith(".1.0"):facts.append({"field":"snmp_sysdescr","value":value,"confidence":0.98})
            elif oid.endswith(".5.0"):facts.append({"field":"hostname","value":value,"confidence":0.98})
            elif oid.endswith(".2.0"):facts.append({"field":"snmp_sysobjectid","value":value,"confidence":1.0})
        object_id=next((f["value"] for f in facts if f["field"]=="snmp_sysobjectid"),"")
        match=next((vendor for enterprise,vendor in ENTERPRISE_VENDORS.items() if f".1.3.6.1.4.1.{enterprise}." in f".{object_id}." or f"enterprises.{enterprise}." in f"{object_id}."),None)
        if match:facts.append({"field":"manufacturer","value":match,"confidence":0.99})
        return [DiscoveryResult(self.name,target,{"sections":sections},facts)]
