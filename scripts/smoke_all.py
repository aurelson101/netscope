#!/usr/bin/env python3
import argparse,json,time,urllib.error,urllib.parse,urllib.request
from datetime import datetime,timezone
from pathlib import Path

def main():
    parser=argparse.ArgumentParser();parser.add_argument("--base",default="http://localhost:8080/api/v1");parser.add_argument("--username",default="admin@netscope.local");parser.add_argument("--password",required=True);parser.add_argument("--scan",action="store_true");args=parser.parse_args();results=[]
    def request(path,method="GET",body=None,auth=True):
        started=time.perf_counter();headers={"Content-Type":"application/json"}
        if auth:headers["Authorization"]="Bearer "+token
        try:
            req=urllib.request.Request(args.base+path,data=json.dumps(body).encode() if body is not None else None,headers=headers,method=method);response=urllib.request.urlopen(req,timeout=120);raw=response.read();value=json.loads(raw) if raw and "json" in response.headers.get("Content-Type","") else raw.decode(errors="replace");results.append({"path":path,"method":method,"status":response.status,"duration_ms":round((time.perf_counter()-started)*1000,1),"ok":True});return value
        except urllib.error.HTTPError as exc:
            detail=exc.read().decode(errors="replace");results.append({"path":path,"method":method,"status":exc.code,"duration_ms":round((time.perf_counter()-started)*1000,1),"ok":False,"error":detail});raise
    form=urllib.parse.urlencode({"username":args.username,"password":args.password}).encode();req=urllib.request.Request(args.base+"/auth/login",data=form,headers={"Content-Type":"application/x-www-form-urlencoded"});token=json.load(urllib.request.urlopen(req,timeout=10))["access_token"]
    endpoints=["/dashboard","/alerts","/assets","/ipam/prefixes","/ipam/addresses","/networks","/scans","/scan-profiles","/topology","/vendors","/archives/assets","/auth/mfa/status","/credentials","/sites","/vlans","/network-devices","/routes","/wireless","/device-roles","/reports/options","/smtp/status","/system/monitoring","/passive-connectors","/probes"]
    values={path:request(path) for path in endpoints}
    if values["/network-devices"] and values["/network-devices"][0].get("ports"):request("/switch-ports/"+values["/network-devices"][0]["ports"][0]["id"]+"/metrics")
    test_site=request("/sites","POST",{"name":"Smoke site temporaire "+datetime.now().strftime("%H%M%S"),"description":"Suppression automatique"});request("/sites/"+test_site["id"],"DELETE")
    assets=values["/assets"]
    if assets:
        asset_id=assets[0]["id"]
        for suffix in ("","/evidence","/history","/identity-history","/metadata","/raw-observations"):request(f"/assets/{asset_id}{suffix}")
    prefixes=values["/ipam/prefixes"]
    dns_prefix=next((x for x in prefixes if x.get("dns_servers")),None)
    if dns_prefix and assets:
        candidate=next((a for a in assets if a.get("addresses")),assets[0]);request("/dns/test","POST",{"server":dns_prefix["dns_servers"][0],"ip_address":candidate["addresses"][0]["address"]})
    request("/topology/refresh","POST")
    test_prefix=request("/ipam/prefixes","POST",{"prefix":"10.254.254.0/30","name":"Smoke test temporaire","status":"active"})
    test_vlan=request("/vlans","POST",{"vlan_id":4094,"name":"Smoke VLAN temporaire","site_id":None,"prefix_id":test_prefix["id"]});request("/vlans/"+test_vlan["id"],"DELETE");request("/ipam/prefixes/"+test_prefix["id"],"DELETE")
    test_network=request("/networks","POST",{"cidr":"10.254.253.0/30","name":"Smoke réseau temporaire","state":"authorized"});request("/networks/"+test_network["id"],"DELETE")
    if args.scan:
        profiles=values["/scan-profiles"];fast=next((x for x in profiles if x["name"]=="Inventaire rapide"),None)
        target=prefixes[0]["prefix"] if prefixes else None
        if fast and target:
            job=request("/scans","POST",{"target":target,"profile_id":fast["id"]});deadline=time.time()+120
            while time.time()<deadline:
                current=next(x for x in request("/scans") if x["id"]==job["id"])
                if current["status"] in ("completed","failed"):
                    if current["status"]!="completed":results.append({"path":"scan-result","ok":False,"error":current.get("error")})
                    break
                time.sleep(1)
    report={"timestamp":datetime.now(timezone.utc).isoformat(),"summary":{"total":len(results),"passed":sum(x["ok"] for x in results),"failed":sum(not x["ok"] for x in results)},"results":results};Path("logs/reports").mkdir(parents=True,exist_ok=True);name=datetime.now().strftime("smoke-%Y%m%d-%H%M%S.json");Path("logs/reports",name).write_text(json.dumps(report,indent=2,ensure_ascii=False));print(json.dumps(report["summary"]));print("logs/reports/"+name)

if __name__=="__main__":main()
