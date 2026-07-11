import { FormEvent, useEffect, useMemo, useState } from "react";
import { Building2, Globe2, Plus, Server, Trash2 } from "lucide-react";
import { api, Asset } from "../lib/api";
import { Layout } from "../components/Layout";
export function Datacenter() {
  const [tab, setTab] = useState("overview"),
    [sites, setSites] = useState<any[]>([]),
    [vlans, setVlans] = useState<any[]>([]),
    [prefixes, setPrefixes] = useState<any[]>([]),
    [addresses, setAddresses] = useState<any[]>([]),
    [assets, setAssets] = useState<Asset[]>([]),
    [error, setError] = useState("");
  const load = () => {
    api<any[]>("/sites").then(setSites);
    api<any[]>("/vlans").then(setVlans);
    api<any[]>("/ipam/prefixes").then(setPrefixes);
    api<any[]>("/ipam/addresses").then(setAddresses);
    api<Asset[]>("/assets").then(setAssets);
  };
  useEffect(load, []);
  const prefixByVlan = (id: string) => prefixes.find((p) => p.vlan_id === id);
  const dcAssets = useMemo(
    () =>
      assets.filter((a) =>
        addresses.some(
          (x) =>
            x.asset_id === a.id &&
            prefixes.some((p) => p.id === x.prefix_id && p.vlan_id),
        ),
      ),
    [assets, addresses, prefixes],
  );
  async function site(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const form = e.currentTarget;
    const f = new FormData(form);
    try {
      await api("/sites", {
        method: "POST",
        body: JSON.stringify({
          name: f.get("name"),
          description: f.get("description") || null,
        }),
      });
      form.reset();
      setError("");
      load();
    } catch (x: any) {
      setError(x.message);
    }
  }
  async function vlan(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const form = e.currentTarget;
    const f = new FormData(form);
    try {
      await api("/vlans", {
        method: "POST",
        body: JSON.stringify({
          vlan_id: Number(f.get("vlan_id")),
          name: f.get("name"),
          site_id: f.get("site_id") || null,
          prefix_id: f.get("prefix_id"),
        }),
      });
      form.reset();
      setError("");
      load();
    } catch (x: any) {
      setError(x.message);
    }
  }
  async function equipment(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const form = e.currentTarget;
    const f = new FormData(form),
      services = String(f.get("services") || "")
        .split(",")
        .map((x) => x.trim())
        .filter(Boolean)
        .map((x) => {
          const [protocolPort, name] = x.split("="),
            [protocol, port] = protocolPort.includes("/")
              ? protocolPort.split("/")
              : ["tcp", protocolPort];
          return { protocol, port: Number(port), name: name || null };
        });
    try {
      await api("/datacenter/equipment", {
        method: "POST",
        body: JSON.stringify({
          hostname: f.get("hostname"),
          ip_address: f.get("ip_address"),
          site_id: f.get("site_id"),
          vlan_id: f.get("vlan_id"),
          description: f.get("description") || null,
          manufacturer: f.get("manufacturer") || null,
          model: f.get("model") || null,
          device_type: f.get("device_type"),
          operating_system: f.get("operating_system") || null,
          services,
        }),
      });
      form.reset();
      setError("");
      load();
    } catch (x: any) {
      setError(x.message);
    }
  }
  async function removeVlan(id: string) {
    if (confirm("Supprimer ce VLAN ? Le préfixe IPAM sera conservé."))
      try {
        await api("/vlans/" + id, { method: "DELETE" });
        load();
      } catch (x: any) {
        setError(x.message);
      }
  }
  return (
    <Layout title="Datacenter">
      <div className="tabs">
        {[
          ["overview", "Vue d’ensemble"],
          ["sites", "Sites et lieux"],
          ["vlans", "VLAN et capacités IP"],
          ["equipment", "Équipements et services"],
        ].map(([k, l]) => (
          <button
            key={k}
            className={tab === k ? "active" : ""}
            onClick={() => setTab(k)}
          >
            {l}
          </button>
        ))}
      </div>
      {error && <div className="error">{error}</div>}
      {tab === "overview" && (
        <>
          <div className="metrics">
            <Metric label="Sites" value={sites.length} icon={<Building2 />} />
            <Metric label="VLAN" value={vlans.length} icon={<Globe2 />} />
            <Metric
              label="Équipements"
              value={dcAssets.length}
              icon={<Server />}
            />
            <Metric
              label="IP utilisées"
              value={
                addresses.filter((a) =>
                  prefixes.some((p) => p.id === a.prefix_id && p.vlan_id),
                ).length
              }
              icon={<Globe2 />}
            />
          </div>
          <VlanTable
            vlans={vlans}
            prefixByVlan={prefixByVlan}
            remove={removeVlan}
          />
        </>
      )}
      {tab === "sites" && (
        <div className="split">
          <Form title="Ajouter un site / lieu" submit={site}>
            <label>
              Nom
              <input name="name" required placeholder="Datacenter Paris" />
            </label>
            <label>
              Description
              <input
                name="description"
                placeholder="Bâtiment, salle, adresse…"
              />
            </label>
          </Form>
          <article className="panel tablePanel">
            <table>
              <thead>
                <tr>
                  <th>Site</th>
                  <th>Description</th>
                </tr>
              </thead>
              <tbody>
                {sites.map((s) => (
                  <tr key={s.id}>
                    <td>{s.name}</td>
                    <td>{s.description || "—"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </article>
        </div>
      )}
      {tab === "vlans" && (
        <>
          <Form title="Créer un VLAN sur un réseau enregistré" submit={vlan}>
            <div className="dcForm">
              <label>
                ID VLAN
                <input
                  name="vlan_id"
                  type="number"
                  min="1"
                  max="4094"
                  required
                />
              </label>
              <label>
                Nom
                <input name="name" required />
              </label>
              <label>
                Site
                <select name="site_id" required>
                  <option value="">Choisir…</option>
                  {sites.map((s) => (
                    <option key={s.id} value={s.id}>
                      {s.name}
                    </option>
                  ))}
                </select>
              </label>
              <label>
                Réseau IPAM
                <select name="prefix_id" required>
                  <option value="">Choisir…</option>
                  {prefixes
                    .filter((p) => !p.vlan_id)
                    .map((p) => (
                      <option key={p.id} value={p.id}>
                        {p.prefix} — {p.name}
                      </option>
                    ))}
                </select>
              </label>
            </div>
          </Form>
          <VlanTable
            vlans={vlans}
            prefixByVlan={prefixByVlan}
            remove={removeVlan}
          />
        </>
      )}
      {tab === "equipment" && (
        <>
          <Form title="Ajouter un équipement" submit={equipment}>
            <div className="dcForm">
              <label>
                Nom
                <input name="hostname" required />
              </label>
              <label>
                Site
                <select name="site_id" required>
                  <option value="">Choisir…</option>
                  {sites.map((s) => (
                    <option key={s.id} value={s.id}>
                      {s.name}
                    </option>
                  ))}
                </select>
              </label>
              <label>
                VLAN
                <select name="vlan_id" required>
                  <option value="">Choisir…</option>
                  {vlans
                    .filter((v) => prefixByVlan(v.id))
                    .map((v) => (
                      <option key={v.id} value={v.id}>
                        VLAN {v.vlan_id} — {v.name} (
                        {prefixByVlan(v.id)?.prefix})
                      </option>
                    ))}
                </select>
              </label>
              <label>
                Adresse IP
                <input
                  name="ip_address"
                  required
                  placeholder="IP appartenant au VLAN"
                />
              </label>
              <label>
                Type
                <select name="device_type">
                  <option>server</option>
                  <option>switch</option>
                  <option>router</option>
                  <option>firewall</option>
                  <option>storage</option>
                  <option>virtual machine</option>
                </select>
              </label>
              <label>
                Constructeur
                <input name="manufacturer" />
              </label>
              <label>
                Modèle
                <input name="model" />
              </label>
              <label>
                Système
                <input name="operating_system" />
              </label>
              <label>
                Description
                <input name="description" />
              </label>
              <label>
                Services
                <input
                  name="services"
                  placeholder="tcp/443=https, tcp/22=ssh"
                />
              </label>
            </div>
          </Form>
          <article className="panel tablePanel dcTable">
            <table>
              <thead>
                <tr>
                  <th>Nom</th>
                  <th>IP</th>
                  <th>Type</th>
                  <th>Constructeur</th>
                  <th>Services</th>
                </tr>
              </thead>
              <tbody>
                {dcAssets.map((a) => (
                  <tr
                    key={a.id}
                    onClick={() => (location.hash = "#/assets/" + a.id)}
                  >
                    <td>{a.hostname}</td>
                    <td>{a.addresses[0]?.address}</td>
                    <td>{a.device_type}</td>
                    <td>{a.manufacturer || "—"}</td>
                    <td>
                      {a.services
                        .map((s) => `${s.protocol}/${s.port} ${s.name || ""}`)
                        .join(", ") || "—"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </article>
        </>
      )}
    </Layout>
  );
}
function Metric({
  label,
  value,
  icon,
}: {
  label: string;
  value: number;
  icon: any;
}) {
  return (
    <article className="metric">
      <div>
        <span>{label}</span>
        <strong>{value}</strong>
        <small>Datacenter</small>
      </div>
      <i className="blue">{icon}</i>
    </article>
  );
}
function Form({
  title,
  submit,
  children,
}: {
  title: string;
  submit: any;
  children: any;
}) {
  return (
    <article className="panel formPanel">
      <h3>
        <Plus /> {title}
      </h3>
      <form onSubmit={submit}>
        {children}
        <button className="primary">Enregistrer</button>
      </form>
    </article>
  );
}
function VlanTable({
  vlans,
  prefixByVlan,
  remove,
}: {
  vlans: any[];
  prefixByVlan: any;
  remove: any;
}) {
  return (
    <article className="panel tablePanel dcTable">
      <table>
        <thead>
          <tr>
            <th>VLAN</th>
            <th>Nom</th>
            <th>Réseau enregistré</th>
            <th>IP prises</th>
            <th>IP disponibles</th>
            <th>Occupation</th>
            <th></th>
          </tr>
        </thead>
        <tbody>
          {vlans.map((v) => {
            const p = prefixByVlan(v.id);
            return (
              <tr key={v.id}>
                <td>{v.vlan_id}</td>
                <td>{v.name}</td>
                <td className="mono">{p?.prefix || "Non associé"}</td>
                <td>{p?.used || 0}</td>
                <td>{p?.available || 0}</td>
                <td>
                  <span className="confidence">{p?.utilization || 0}%</span>
                </td>
                <td>
                  <button className="icon" onClick={() => remove(v.id)}>
                    <Trash2 />
                  </button>
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </article>
  );
}
