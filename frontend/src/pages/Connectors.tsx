import { FormEvent, useEffect, useState } from "react";
import { Cable, Copy, KeyRound, Trash2 } from "lucide-react";
import { Layout } from "../components/Layout";
import { api } from "../lib/api";

export function Connectors() {
  const [rows,setRows]=useState<any[]>([]),[vrfs,setVrfs]=useState<any[]>([]),[token,setToken]=useState(""),[message,setMessage]=useState("");
  const load=()=>{api<any[]>("/passive-connectors").then(setRows).catch((x)=>setMessage(x.message));api<any[]>("/ipam/vrfs").then(setVrfs).catch(()=>setVrfs([]));};
  useEffect(load,[]);
  async function create(e:FormEvent<HTMLFormElement>){e.preventDefault();const form=e.currentTarget,f=new FormData(form);try{const result:any=await api("/passive-connectors",{method:"POST",body:JSON.stringify({name:f.get("name"),kind:f.get("kind"),vrf_id:f.get("vrf_id")||null})});setToken(result.token);setMessage(result.warning);form.reset();load();}catch(x:any){setMessage(x.message);}}
  async function toggle(row:any){await api(`/passive-connectors/${row.id}?enabled=${!row.enabled}`,{method:"PATCH"});load();}
  async function rotate(id:string){if(!confirm("Révoquer immédiatement l’ancien jeton ?"))return;const result:any=await api(`/passive-connectors/${id}/rotate-token`,{method:"POST"});setToken(result.token);setMessage(result.warning);}
  async function remove(id:string){if(!confirm("Supprimer ce connecteur et son historique anti-rejeu ?"))return;await api(`/passive-connectors/${id}`,{method:"DELETE"});load();}
  return <Layout title="Connecteurs passifs">
    {message&&<div className="hint">{message}</div>}
    {token&&<article className="panel"><h3>Jeton affiché une seule fois</h3><div className="rowActions"><code style={{overflowWrap:"anywhere"}}>{token}</code><button onClick={()=>navigator.clipboard.writeText(token)}><Copy/> Copier</button></div><p className="hint">Envoyez-le dans l’en-tête <code>X-Connector-Token</code> vers <code>POST /api/v1/passive-ingest</code>.</p></article>}
    <div className="split" style={{marginTop:12}}><article className="panel formPanel"><h3><Cable/> Nouveau connecteur</h3><form onSubmit={create}><label>Nom<input name="name" required/></label><label>Source<select name="kind"><option value="dhcp">Journal DHCP</option><option value="arp">Table ARP</option><option value="dns">Journal DNS</option><option value="wireless">Contrôleur Wi-Fi</option><option value="generic">Générique</option></select></label><label>VRF<select name="vrf_id"><option value="">Globale</option>{vrfs.map(v=><option key={v.id} value={v.id}>{v.name}</option>)}</select></label><button className="primary">Créer et générer le jeton</button></form></article>
    <article className="panel"><h3>État des sources</h3><div className="scanList">{rows.map(row=><div key={row.id}><Cable/><span><b>{row.name}</b><small>{row.kind} · {row.event_count} événement(s) · {row.last_seen_at?new Date(row.last_seen_at).toLocaleString("fr"):"jamais contacté"}{row.last_error?` · erreur : ${row.last_error}`:""}</small></span><em className={`badge ${row.enabled?"completed":"failed"}`}>{row.enabled?"actif":"désactivé"}</em><button className="icon" title="Activer/désactiver" onClick={()=>toggle(row)}><Cable/></button><button className="icon" title="Renouveler le jeton" onClick={()=>rotate(row.id)}><KeyRound/></button><button className="icon danger" title="Supprimer" onClick={()=>remove(row.id)}><Trash2/></button></div>)}</div></article></div>
  </Layout>;
}
