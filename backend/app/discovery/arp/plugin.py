import asyncio, re
from app.discovery.base import DiscoveryPlugin, DiscoveryResult
from app.services.vendors import normalize_mac

LINE = re.compile(r"^(?P<ip>\d+\.\d+\.\d+\.\d+)\s+(?P<mac>[0-9a-f:]{17})\s*(?P<vendor>.*)$", re.I)


class ArpPlugin(DiscoveryPlugin):
    name = "arp"
    async def discover(self, target: str, options: dict):
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
