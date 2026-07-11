import asyncio
from app.discovery.base import DiscoveryPlugin
from app.discovery.nmap.parser import parse_nmap_xml


class NmapPlugin(DiscoveryPlugin):
    name = "nmap"
    async def discover(self, target: str, options: dict):
        profile = options.get("profile", "fast")
        args = {"fast":["-sn","-n","-T5","--max-retries","0","--host-timeout","3s","--max-rtt-timeout","500ms"], "standard":["-n","-T4","-sV","-O","--osscan-limit","--version-light","--host-timeout","90s","--script","nbstat,smb-os-discovery,http-title,ssl-cert"], "deep":["-n","-T4","-sV","-O","--host-timeout","180s","--script","nbstat,smb-os-discovery,http-title,ssl-cert,ssh-hostkey"]}.get(profile, ["-sn","-n"])
        default_rate=1000 if profile=="fast" else 100
        proc = await asyncio.create_subprocess_exec("nmap", *args, "-oX", "-", "--max-rate", str(options.get("max_rate", default_rate)), target, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=options.get("timeout", 900))
        if proc.returncode != 0: raise RuntimeError(stderr.decode(errors="replace")[:1000])
        return parse_nmap_xml(stdout.decode(errors="replace"))
