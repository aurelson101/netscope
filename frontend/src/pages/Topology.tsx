import { FormEvent, useEffect, useState } from "react";
import { ArrowLeftRight, Link2, Network, Pencil, RefreshCw, Trash2 } from "lucide-react";
import { api, Asset } from "../lib/api";
import { Layout } from "../components/Layout";
const sourceLabel: Record<string, string> = {
  lldp: "LLDP",
  cdp: "CDP",
  manual: "Manuel",
  inferred_ipam: "Inféré par IPAM",
};
export function Topology() {
  const [data, setData] = useState<any>({ nodes: [], links: [] }),
    [assets, setAssets] = useState<Asset[]>([]),
    [message, setMessage] = useState(""),
    [filter, setFilter] = useState("all");
  const load = () => {
    api("/topology").then(setData);
    api<Asset[]>("/assets").then(setAssets);
  };
  useEffect(load, []);
  const node = (id: string) => data.nodes.find((x: any) => x.id === id);
  async function refresh() {
    const result: any = await api("/topology/refresh", { method: "POST" });
    setMessage(`${result.created} relation(s) inférée(s) ajoutée(s)`);
    load();
  }
  async function create(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const form=e.currentTarget,f = new FormData(form);
    try {
      await api("/topology/links", {
        method: "POST",
        body: JSON.stringify({
          source_asset_id: f.get("source"),
          target_asset_id: f.get("target"),
          source_port: f.get("source_port") || null,
          target_port: f.get("target_port") || null,
        }),
      });
      setMessage("Relation manuelle ajoutée");
      form.reset();
      load();
    } catch (x: any) {
      setMessage(x.message);
    }
  }
  async function edit(link:any,reverse=false){if(link.protocol!=="manual"){setMessage("Les relations LLDP/CDP et IPAM sont en lecture seule");return}const source=reverse?link.source_port:prompt("Port source",link.source_port||"");if(source===null)return;const target=reverse?link.target_port:prompt("Port destination",link.target_port||"");if(target===null)return;try{await api("/topology/links/"+link.id,{method:"PATCH",body:JSON.stringify({source_port:source||null,target_port:target||null,reverse})});setMessage(reverse?"Sens de la relation inversé":"Ports mis à jour");load()}catch(x:any){setMessage(x.message)}}
  async function remove(link:any){if(!confirm("Supprimer cette relation ?"))return;try{await api("/topology/links/"+link.id,{method:"DELETE"});setMessage("Relation supprimée");load()}catch(x:any){setMessage(x.message)}}
  const links=data.links.filter((x:any)=>filter==="all"||x.protocol===filter);
  return (
    <Layout title="Topologie réseau">
      <div className="pageHead">
        <select className="button" value={filter} onChange={e=>setFilter(e.target.value)}><option value="all">Toutes les origines</option><option value="manual">Manuelles</option><option value="lldp">LLDP</option><option value="cdp">CDP</option><option value="inferred_ipam">IPAM inférées</option></select>
        <button className="button" onClick={refresh}>
          <RefreshCw />
          Reconstruire depuis l’IPAM
        </button>
      </div>
      <div className="split">
        <article className="panel">
          <h3>Relations d’infrastructure</h3>
          {links.map((link: any) => (
            <div className="topologyLink" key={link.id}>
              <div>
                <Network />
                <b>{node(link.source)?.label || "Équipement"}</b>
                <small>{link.source_port || "port local"}</small>
              </div>
              <span>
                <em>{sourceLabel[link.protocol] || link.protocol}</em>───→
                <small>{Math.round(link.confidence * 100)}% de confiance</small>
              </span>
              <div>
                <Network />
                <b>{node(link.target)?.label || "Voisin"}</b>
                <small>{link.target_port || "port distant"}</small>
              </div>
              <div className="relationActions">{link.protocol==="manual"&&<><button title="Modifier les ports" onClick={()=>edit(link)}><Pencil/></button><button title="Inverser le sens" onClick={()=>edit(link,true)}><ArrowLeftRight/></button></>}<button className="danger" title="Supprimer" onClick={()=>remove(link)}><Trash2/></button></div>
            </div>
          ))}
          {!links.length && (
            <div className="empty">
              <Network />
              Aucune relation. Utilisez la reconstruction IPAM ou ajoutez un
              lien manuel.
            </div>
          )}
        </article>
        <article className="panel formPanel">
          <h3>
            <Link2 />
            Ajouter une relation manuelle
          </h3>
          <form onSubmit={create}>
            <label>
              Équipement source
              <select name="source" required>
                {assets.map((a) => (
                  <option key={a.id} value={a.id}>
                    {a.hostname || a.addresses[0]?.address || a.id}
                  </option>
                ))}
              </select>
            </label>
            <label>
              Port source
              <input name="source_port" placeholder="LAN, Gi1/0/24…" />
            </label>
            <label>
              Équipement destination
              <select name="target" required>
                {assets.map((a) => (
                  <option key={a.id} value={a.id}>
                    {a.hostname || a.addresses[0]?.address || a.id}
                  </option>
                ))}
              </select>
            </label>
            <label>
              Port destination
              <input name="target_port" placeholder="eth0, Wi-Fi…" />
            </label>
            <button className="primary">Enregistrer la relation</button>
          </form>
          {message && <p className="hint">{message}</p>}
          <p className="hint">
            Les liens IPAM sont des inférences à 60%. Seuls LLDP/CDP et les
            liens manuels sont considérés comme confirmés.
          </p>
        </article>
      </div>
    </Layout>
  );
}
