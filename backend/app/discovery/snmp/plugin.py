import asyncio
from app.discovery.base import DiscoveryPlugin, DiscoveryResult
from app.discovery.snmp.parser import parse_walk

OIDS={
 "system":"1.3.6.1.2.1.1", "interfaces":"1.3.6.1.2.1.2.2.1",
 "if_names":"1.3.6.1.2.1.31.1.1.1", "arp":"1.3.6.1.2.1.4.22.1",
 "fdb":"1.3.6.1.2.1.17.4.3.1", "vlans":"1.3.6.1.2.1.17.7.1.4.3.1",
 "bridge_ports":"1.3.6.1.2.1.17.1.4.1.2",
 "lldp":"1.0.8802.1.1.2.1.4", "cdp":"1.3.6.1.4.1.9.9.23.1.2.1.1",
}


class SnmpPlugin(DiscoveryPlugin):
    name="snmp"
    async def discover(self,target:str,options:dict):
        credential=options.get("credential") or {}
        if credential.get("version")!="3": raise ValueError("SNMPv3 est requis (SNMPv2c doit être explicitement géré séparément)")
        user=credential.get("username")
        if not user: raise ValueError("Nom d'utilisateur SNMPv3 manquant")
        base=["snmpbulkwalk","-v3","-l",credential.get("security_level","authPriv"),"-u",user,"-t",str(options.get("timeout",3)),"-r",str(options.get("retries",1))]
        if credential.get("auth_password"): base += ["-a",credential.get("auth_protocol","SHA"),"-A",credential["auth_password"]]
        if credential.get("privacy_password"): base += ["-x",credential.get("privacy_protocol","AES"),"-X",credential["privacy_password"]]
        sections={}
        for name,oid in OIDS.items():
            proc=await asyncio.create_subprocess_exec(*base,target,oid,stdout=asyncio.subprocess.PIPE,stderr=asyncio.subprocess.PIPE)
            stdout,stderr=await asyncio.wait_for(proc.communicate(),timeout=options.get("section_timeout",30))
            sections[name]=parse_walk(stdout.decode(errors="replace"))
            if name=="system" and proc.returncode!=0: raise RuntimeError(stderr.decode(errors="replace")[:500])
        facts=[{"field":"ip","value":target,"confidence":1.0},{"field":"status","value":"online","confidence":1.0}]
        system={row["oid"]:row["value"] for row in sections["system"]}
        for oid,value in system.items():
            if oid.endswith(".1.0"):facts.append({"field":"snmp_sysdescr","value":value,"confidence":0.98})
            elif oid.endswith(".5.0"):facts.append({"field":"hostname","value":value,"confidence":0.98})
            elif oid.endswith(".2.0"):facts.append({"field":"snmp_sysobjectid","value":value,"confidence":1.0})
        return [DiscoveryResult(self.name,target,{"sections":sections},facts)]
