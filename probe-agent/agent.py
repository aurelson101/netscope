import asyncio,ipaddress,logging,os,time
import httpx
from app.discovery.arp.plugin import ArpPlugin
from app.discovery.dns.plugin import DNSPlugin
from app.discovery.icmp.plugin import IcmpPlugin
from app.discovery.nmap.plugin import NmapPlugin

logging.basicConfig(level=os.getenv("LOG_LEVEL","INFO"));log=logging.getLogger("netscope.probe")
URL=os.environ["NETSCOPE_URL"].rstrip("/")+"/api/v1";TOKEN=os.environ["PROBE_TOKEN"]
POLL=max(int(os.getenv("POLL_SECONDS","5")),2);VERIFY=os.getenv("VERIFY_TLS","true").lower() not in ("0","false","no")
PLUGINS={plugin.name:plugin for plugin in (IcmpPlugin(),ArpPlugin(),NmapPlugin(),DNSPlugin())}

def reachable_networks():
    """Return kernel routes visible from the probe without running a shell."""
    networks=set()
    try:
        with open("/proc/net/route",encoding="ascii") as routes:
            next(routes,None)
            for line in routes:
                fields=line.split()
                if len(fields)<8 or not int(fields[3],16)&1:continue
                address=int(fields[1],16).to_bytes(4,"little");mask=int(fields[7],16).to_bytes(4,"little")
                networks.add(str(ipaddress.ip_network((str(ipaddress.ip_address(address)),str(ipaddress.ip_address(mask))),strict=False)))
    except (OSError,ValueError):log.exception("route_inventory_failed")
    networks.discard("0.0.0.0/0")
    return sorted(networks,key=lambda value:int(ipaddress.ip_network(value).network_address))

def targets(module,target,discovered):
    if module=="dns" and "/" in target:
        if discovered:return sorted(discovered,key=lambda x:int(ipaddress.ip_address(x)))
        network=ipaddress.ip_network(target,strict=False);return [str(network.network_address)] if network.num_addresses==1 else []
    return [target]

def serialize(result):return {"source":result.source,"target":result.target,"raw":result.raw,"facts":result.facts}

async def execute(task):
    found=set();observations=[]
    for module in task["modules"]:
        if module not in PLUGINS:raise RuntimeError(f"Module non disponible: {module}")
        for target in targets(module,task["target"],found):
            results=await PLUGINS[module].discover(target,dict(task.get("options",{}).get(module,{})))
            for result in results:found.add(result.target);observations.append(serialize(result))
    return observations

async def main():
    headers={"X-Probe-Token":TOKEN};capabilities=sorted(PLUGINS)
    async with httpx.AsyncClient(base_url=URL,headers=headers,verify=VERIFY,timeout=120) as client:
        while True:
            try:
                response=await client.post("/probe/heartbeat",json={"version":"1.1.0","capabilities":capabilities,"reachable_networks":reachable_networks()});response.raise_for_status()
                response=await client.get("/probe/tasks/next")
                if response.status_code==204:await asyncio.sleep(POLL);continue
                response.raise_for_status();task=response.json();log.info("task_started id=%s target=%s",task["id"],task["target"])
                try:payload={"claim_token":task["claim_token"],"status":"completed","observations":await execute(task)}
                except Exception as exc:log.exception("task_failed id=%s",task["id"]);payload={"claim_token":task["claim_token"],"status":"failed","error":str(exc)[:2000],"observations":[]}
                result=await client.post(f"/probe/tasks/{task['id']}/result",json=payload);result.raise_for_status();log.info("task_finished id=%s status=%s",task["id"],payload["status"])
            except Exception:log.exception("probe_cycle_failed");await asyncio.sleep(min(POLL*3,30))

if __name__=="__main__":asyncio.run(main())
