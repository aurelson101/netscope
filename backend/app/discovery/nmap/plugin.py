import asyncio
from app.discovery.base import DiscoveryPlugin
from app.discovery.nmap.parser import parse_nmap_xml

NMAP_PROFILES={
    "fast":["-sn","-n","-T5","--max-retries","0","--host-timeout","3s","--max-rtt-timeout","500ms"],
    "standard":["-n","-T4","-sV","-O","--osscan-limit","--version-light","--host-timeout","90s","--script","nbstat,smb-os-discovery,http-title,ssl-cert"],
    "deep":["-n","-T4","-sV","-O","--host-timeout","180s","--script","nbstat,smb-os-discovery,http-title,ssl-cert,ssh-hostkey"],
    "udp":["-n","-T4","-sU","-sV","--version-light","--top-ports","100","--host-timeout","180s"],
}

def build_nmap_args(options:dict)->list[str]:
    profile=options.get("profile","fast")
    if profile not in NMAP_PROFILES:raise ValueError(f"Profil Nmap non supporté: {profile}")
    default_rate=1000 if profile=="fast" else (50 if profile=="udp" else 100)
    max_rate=int(options.get("max_rate",default_rate))
    if not 1<=max_rate<=5000:raise ValueError("Le débit Nmap doit être compris entre 1 et 5000 paquets/s")
    return [*NMAP_PROFILES[profile],"-oX","-","--max-rate",str(max_rate)]


class NmapPlugin(DiscoveryPlugin):
    name = "nmap"
    async def discover(self, target: str, options: dict):
        args=build_nmap_args(options)
        proc = await asyncio.create_subprocess_exec("nmap", *args, target, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
        try:
            stdout,stderr=await asyncio.wait_for(proc.communicate(),timeout=options.get("timeout",900))
        except TimeoutError:
            proc.kill();await proc.communicate()
            raise RuntimeError("Le scan Nmap a dépassé le délai autorisé") from None
        if proc.returncode != 0: raise RuntimeError(stderr.decode(errors="replace")[:1000])
        return parse_nmap_xml(stdout.decode(errors="replace"))
