import asyncio, socket
import dns.reversename
import dns.resolver
from app.discovery.base import DiscoveryPlugin, DiscoveryResult


class DNSPlugin(DiscoveryPlugin):
    name = "dns"
    async def discover(self, target: str, options: dict):
        servers=options.get("servers") or []
        if servers:
            resolver=dns.resolver.Resolver(configure=False);resolver.nameservers=servers;resolver.timeout=options.get("timeout",2);resolver.lifetime=options.get("timeout",2)
            try:
                answers=await asyncio.to_thread(resolver.resolve,dns.reversename.from_address(target),"PTR")
                hostname=str(next(iter(answers))).rstrip(".")
                return [DiscoveryResult(self.name,target,{"hostname":hostname,"dns_servers":servers},[{"field":"hostname","value":hostname,"confidence":0.95},{"field":"dns_source","value":servers[0],"confidence":1}])]
            except Exception:return []
        loop = asyncio.get_running_loop()
        try:
            hostname, aliases, _ = await asyncio.wait_for(loop.run_in_executor(None, socket.gethostbyaddr, target), options.get("timeout", 2))
        except (OSError, asyncio.TimeoutError): return []
        return [DiscoveryResult(self.name, target, {"hostname":hostname,"aliases":aliases}, [{"field":"hostname","value":hostname,"confidence":0.8}])]
