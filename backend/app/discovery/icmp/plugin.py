import asyncio
from app.discovery.base import DiscoveryPlugin, DiscoveryResult


class IcmpPlugin(DiscoveryPlugin):
    name="icmp"
    async def discover(self,target:str,options:dict):
        proc=await asyncio.create_subprocess_exec("ping","-c","1","-W",str(options.get("timeout",1)),target,stdout=asyncio.subprocess.DEVNULL,stderr=asyncio.subprocess.DEVNULL)
        code=await proc.wait()
        return [DiscoveryResult(self.name,target,{"reachable":code==0},[{"field":"status","value":"online","confidence":0.9}])] if code==0 else []
