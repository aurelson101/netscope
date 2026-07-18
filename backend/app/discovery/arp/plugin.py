import asyncio, ipaddress, re
from app.discovery.base import DiscoveryPlugin, DiscoveryResult
from app.services.vendors import normalize_mac

LINE = re.compile(r"^(?P<ip>\d+\.\d+\.\d+\.\d+)\s+(?P<mac>[0-9a-f:]{17})\s*(?P<vendor>.*)$", re.I)
NDP_LINE = re.compile(r"^(?P<ip>[0-9a-f:]+(?:%\S+)?)\s+dev\s+\S+\s+lladdr\s+(?P<mac>[0-9a-f:]{17})\s+(?P<state>\S+)", re.I)


class ArpPlugin(DiscoveryPlugin):
    name = "arp"
    async def discover(self, target: str, options: dict):
        if ipaddress.ip_network(target, strict=False).version == 6:
            proc = await asyncio.create_subprocess_exec("ip", "-6", "neigh", "show", target, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
            stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=options.get("timeout", 30))
            results=[]
            for line in stdout.decode(errors="replace").splitlines():
                match=NDP_LINE.match(line.strip())
                if not match: continue
                row=match.groupdict(); ip=row["ip"].split("%",1)[0]
                facts=[{"field":"ip","value":str(ipaddress.ip_address(ip)),"confidence":1},{"field":"mac","value":normalize_mac(row["mac"]),"confidence":1}]
                results.append(DiscoveryResult(self.name,ip,row,facts))
            return results
        proc = await asyncio.create_subprocess_exec("arp-scan", "--plain", "--localnet" if options.get("localnet") else target, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
        stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=options.get("timeout", 120))
        results=[]
        for line in stdout.decode(errors="replace").splitlines():
            match=LINE.match(line)
            if match:
                row=match.groupdict(); facts=[{"field":"ip","value":row["ip"],"confidence":1},{"field":"mac","value":normalize_mac(row["mac"]),"confidence":1}]
                if row["vendor"]: facts.append({"field":"manufacturer","value":row["vendor"],"confidence":0.75})
                results.append(DiscoveryResult(self.name,row["ip"],row,facts))
        return results
