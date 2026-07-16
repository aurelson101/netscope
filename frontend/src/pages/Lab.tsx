import { useEffect, useState } from "react";
import { Cable, Globe2, Network, Router, Server } from "lucide-react";
import { api, Asset } from "../lib/api";
import { Layout } from "../components/Layout";
export function Lab() {
  const [assets, setAssets] = useState<Asset[]>([]),
    [prefixes, setPrefixes] = useState<any[]>([]),
    [networks, setNetworks] = useState<any[]>([]),
    [devices, setDevices] = useState<any[]>([]),
    [vlans, setVlans] = useState<any[]>([]);
  useEffect(() => {
    api<Asset[]>("/assets").then(setAssets);
    api<any[]>("/ipam/prefixes").then(setPrefixes);
    api<any[]>("/networks").then(setNetworks);
    api<any[]>("/network-devices").then(setDevices);
    api<any[]>("/vlans").then(setVlans);
  }, []);
  const ports = devices.reduce((n, d) => n + (d.ports?.length || 0), 0);
  const monitoredPorts = devices.flatMap((device) =>
    (device.ports || []).filter((port: any) => port.metric).map((port: any) => ({...port,device:device.sys_name || device.management_ip || "Équipement"})),
  ).sort((a: any,b: any) => Math.max(b.metric.in_utilization || 0,b.metric.out_utilization || 0)-Math.max(a.metric.in_utilization || 0,a.metric.out_utilization || 0));
  return (
    <Layout title="Infrastructure Lab">
      <div className="labIntro">
        <div>
          <h1>Source de vérité infrastructure</h1>
          <p>
            Gérez les équipements, l’adressage IP, les réseaux, VLAN et
            relations depuis un espace cohérent.
          </p>
        </div>
      </div>
      <div className="labGrid">
        <a href="#/assets" className="panel labCard">
          <Server />
          <div>
            <strong>{assets.length}</strong>
            <h3>Équipements</h3>
            <p>Inventaire, identité, système et services.</p>
          </div>
        </a>
        <a href="#/ipam" className="panel labCard">
          <Globe2 />
          <div>
            <strong>{prefixes.length}</strong>
            <h3>Préfixes IPAM</h3>
            <p>Adresses, DNS, rôles et utilisation.</p>
          </div>
        </a>
        <a href="#/networks" className="panel labCard">
          <Network />
          <div>
            <strong>{networks.length}</strong>
            <h3>Réseaux</h3>
            <p>Périmètres de scan enregistrés et suppression.</p>
          </div>
        </a>
        <a href="#/topology" className="panel labCard">
          <Cable />
          <div>
            <strong>{ports}</strong>
            <h3>Interfaces et relations</h3>
            <p>Ports, LLDP/CDP et corrélations physiques.</p>
          </div>
        </a>
      </div>
      <div className="metrics labMetrics">
        <article className="metric">
          <div>
            <span>Équipements réseau</span>
            <strong>{devices.length}</strong>
            <small>SNMP / commutateurs / routeurs</small>
          </div>
          <i className="blue">
            <Router />
          </i>
        </article>
        <article className="metric">
          <div>
            <span>VLAN collectés</span>
            <strong>{vlans.length}</strong>
            <small>Associés aux interfaces</small>
          </div>
          <i className="green">
            <Network />
          </i>
        </article>
      </div>
      <article className="panel tablePanel labTable">
        <div className="labTableHead"><div><h3>Métriques d’interfaces SNMP</h3><p>Interfaces les plus utilisées lors de la dernière collecte.</p></div></div>
        <table><thead><tr><th>Équipement</th><th>Interface</th><th>Entrant</th><th>Sortant</th><th>Utilisation max.</th><th>Erreurs</th></tr></thead><tbody>{monitoredPorts.slice(0,20).map((port:any)=><tr key={port.id}><td>{port.device}</td><td>{port.name || port.description || `ifIndex ${port.if_index}`}</td><td>{formatRate(port.metric.in_bps)}</td><td>{formatRate(port.metric.out_bps)}</td><td>{Math.max(port.metric.in_utilization || 0,port.metric.out_utilization || 0).toFixed(1)} %</td><td>{(port.metric.in_errors || 0)+(port.metric.out_errors || 0)}</td></tr>)}</tbody></table>
        {!monitoredPorts.length && <p className="hint">Deux collectes SNMP sont nécessaires pour calculer les débits.</p>}
      </article>
      <article className="panel tablePanel labTable">
        <div className="labTableHead">
          <div>
            <h3>Équipements récents</h3>
            <p>Les dix derniers équipements observés sur l’infrastructure.</p>
          </div>
          <a href="#/assets">Voir l’inventaire</a>
        </div>
        <table>
          <thead>
            <tr>
              <th>Nom</th>
              <th>Adresse principale</th>
              <th>Type</th>
              <th>Constructeur</th>
              <th>Système</th>
              <th>État</th>
            </tr>
          </thead>
          <tbody>
            {assets.slice(0, 10).map((a) => (
              <tr
                key={a.id}
                onClick={() => (location.hash = "#/assets/" + a.id)}
              >
                <td>{a.hostname || "Sans nom"}</td>
                <td className="mono">{a.addresses[0]?.address || "—"}</td>
                <td>{a.device_type}</td>
                <td>{a.manufacturer || "—"}</td>
                <td>{a.operating_system || "—"}</td>
                <td>
                  <span className={"badge " + a.status}>{a.status}</span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </article>
    </Layout>
  );
}
function formatRate(value:number|null|undefined){if(value==null)return "—";if(value>=1e9)return `${(value/1e9).toFixed(2)} Gb/s`;if(value>=1e6)return `${(value/1e6).toFixed(2)} Mb/s`;if(value>=1e3)return `${(value/1e3).toFixed(1)} kb/s`;return `${value.toFixed(0)} b/s`}
