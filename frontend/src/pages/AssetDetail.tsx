import { useEffect, useState } from "react";
import { ArrowLeft, Clock, Network, Server } from "lucide-react";
import { api, Asset } from "../lib/api";
import { canOperate, useCurrentUser } from "../lib/permissions";
import { Layout } from "../components/Layout";
export function AssetDetail({ id }: { id: string }) {
  const editable = canOperate(useCurrentUser());
  const [a, setA] = useState<Asset>(),
    [tab, setTab] = useState("overview"),
    [evidence, setEvidence] = useState<any[]>([]),
    [history, setHistory] = useState<any[]>([]),
    [raw, setRaw] = useState<any[]>([]),
    [error, setError] = useState("");
  useEffect(() => {
    api<Asset>("/assets/" + id)
      .then(setA)
      .catch((x) => setError(x.message));
    api<any[]>("/assets/" + id + "/evidence")
      .then(setEvidence)
      .catch(() => setEvidence([]));
    api<any[]>("/assets/" + id + "/history")
      .then(setHistory)
      .catch(() => setHistory([]));
    api<any[]>("/assets/" + id + "/raw-observations")
      .then(setRaw)
      .catch(() => setRaw([]));
  }, [id]);
  if (error)
    return (
      <Layout title="Actif">
        <a href="#/assets" className="back">
          <ArrowLeft />
          Retour à l’inventaire
        </a>
        <div className="error">Chargement impossible : {error}</div>
      </Layout>
    );
  if (!a)
    return (
      <Layout title="Actif">
        <div className="loading">Chargement…</div>
      </Layout>
    );
  const tabs: any = {
    overview: "Vue d’ensemble",
    network: "Réseau",
    services: "Services",
    identification: "Identification",
    history: "Historique",
    ...(editable ? { raw: "Données brutes" } : {}),
  };
  return (
    <Layout title={a.hostname || a.addresses[0]?.address || "Actif"}>
      <a href="#/assets" className="back">
        <ArrowLeft />
        Retour à l’inventaire
      </a>
      <div className="assetHero">
        <div className="deviceIcon">
          <Server />
        </div>
        <div>
          <h1>{a.hostname || "Appareil inconnu"}</h1>
          <p>
            {a.manufacturer || "Constructeur inconnu"} ·{" "}
            {a.model || a.device_type}
          </p>
        </div>
        <span className={"status " + a.status}>{a.status}</span>
        <div className="score">
          <strong>{Math.round(a.confidence * 100)}%</strong>
          <small>Confiance</small>
        </div>
      </div>
      <div className="tabs">
        {Object.entries(tabs).map(([key, label]) => (
          <button
            key={key}
            className={tab === key ? "active" : ""}
            onClick={() => setTab(key)}
          >
            {String(label)}
          </button>
        ))}
      </div>
      {tab === "overview" && (
        <div className="detailGrid">
          <Card title="Identité">
            <Field l="Nom d’hôte" v={a.hostname} />
            <Field l="Constructeur" v={a.manufacturer} />
            <Field l="Modèle" v={a.model} />
            <Field l="Type" v={a.device_type} />
            <Field l="Système" v={a.operating_system} />
          </Card>
          <Card title="Activité">
            <Field
              l="Premier vu"
              v={new Date(a.first_seen).toLocaleString("fr")}
            />
            <Field
              l="Dernier vu"
              v={new Date(a.last_seen).toLocaleString("fr")}
            />
            <Field l="Statut" v={a.status} />
          </Card>
        </div>
      )}
      {tab === "network" && (
        <Card title="Interfaces et adresses">
          <div className="rows">
            {a.addresses.map((x) => (
              <div key={x.address}>
                <Network />
                <b>{x.address}</b>
                <span>IPv{x.version}</span>
              </div>
            ))}
            {a.identifiers.map((x) => (
              <div key={x.kind + x.value}>
                <Network />
                <b>{x.value}</b>
                <span>{x.kind}</span>
              </div>
            ))}
          </div>
        </Card>
      )}
      {tab === "services" && (
        <Card title="Services détectés">
          <table>
            <thead>
              <tr>
                <th>Protocole</th>
                <th>Port</th>
                <th>Service</th>
                <th>Produit</th>
                <th>Version</th>
              </tr>
            </thead>
            <tbody>
              {a.services.map((s) => (
                <tr key={s.protocol + s.port}>
                  <td>{s.protocol}</td>
                  <td>{s.port}</td>
                  <td>{s.name}</td>
                  <td>{s.product}</td>
                  <td>{s.version}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </Card>
      )}
      {tab === "identification" && (
        <Card title="Preuves d’identification">
          <div className="rows">
            {evidence.map((x) => (
              <div key={x.id}>
                <span className="source">{x.source}</span>
                <b>
                  {x.field}: {x.value}
                </b>
                <span>{Math.round(x.confidence * 100)}%</span>
              </div>
            ))}
          </div>
        </Card>
      )}
      {tab === "history" && (
        <Card title="Chronologie">
          <div className="timeline">
            {history.map((x) => (
              <div key={x.id}>
                <Clock />
                <span>
                  <b>{x.event_type}</b>
                  <small>
                    {x.old_value || "—"} → {x.new_value || "—"}
                  </small>
                </span>
                <time>{new Date(x.created_at).toLocaleString("fr")}</time>
              </div>
            ))}
          </div>
        </Card>
      )}
      {tab === "raw" && (
        <Card title="Données brutes">
          <div className="rawList">
            {raw.map((x) => (
              <details key={x.id}>
                <summary>
                  {x.source} · {new Date(x.observed_at).toLocaleString("fr")}
                </summary>
                <pre>{JSON.stringify(x.raw_data, null, 2)}</pre>
              </details>
            ))}
            {!raw.length && (
              <p>Aucune observation disponible ou permissions insuffisantes.</p>
            )}
          </div>
        </Card>
      )}
    </Layout>
  );
}
function Card({ title, children }: { title: string; children: any }) {
  return (
    <article className="panel card">
      <h3>{title}</h3>
      {children}
    </article>
  );
}
function Field({ l, v }: { l: string; v: any }) {
  return (
    <div className="field">
      <span>{l}</span>
      <b>{v || "—"}</b>
    </div>
  );
}
