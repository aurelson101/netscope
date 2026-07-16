import { useEffect, useState } from "react";
import { AlertTriangle, Check, ExternalLink, RotateCw } from "lucide-react";
import { Layout } from "../components/Layout";
import { api } from "../lib/api";
import { canOperate, useCurrentUser } from "../lib/permissions";

const labels: Record<string, string> = { open: "Ouvertes", acknowledged: "Acquittées", resolved: "Résolues" };

export function Alerts() {
  const editable = canOperate(useCurrentUser());
  const [status, setStatus] = useState("open"),
    [alerts, setAlerts] = useState<any[]>([]),
    [error, setError] = useState("");
  const load = () => {
    setError("");
    api<any[]>(`/alerts?status=${status}`).then(setAlerts).catch((x) => setError(x.message));
  };
  useEffect(load, [status]);
  const action = async (id: string, name: "acknowledge" | "resolve") => {
    try { await api(`/alerts/${id}/${name}`, { method: "POST" }); load(); }
    catch (x: any) { setError(x.message); }
  };
  return (
    <Layout title="Alertes réseau">
      <div className="toolbar alertToolbar">
        {Object.entries(labels).map(([value, label]) => (
          <button className={status === value ? "primary" : "button"} onClick={() => setStatus(value)} key={value}>{label}</button>
        ))}
        <button className="icon" onClick={load} title="Actualiser"><RotateCw /></button>
      </div>
      {error && <div className="error">{error}</div>}
      <article className="panel">
        <div className="alertList">
          {alerts.map((alert) => (
            <div className={`alertItem ${alert.severity}`} key={alert.id}>
              <AlertTriangle />
              <span>
                <b>{alert.title}</b>
                <small>{alert.message}</small>
                <time>Début : {new Date(alert.first_seen).toLocaleString("fr")} · Dernier signal : {new Date(alert.last_seen).toLocaleString("fr")}</time>
              </span>
              {alert.asset_id && <a className="button" href={`#/assets/${alert.asset_id}`}><ExternalLink /> Actif</a>}
              {editable && alert.status === "open" && <button onClick={() => action(alert.id,"acknowledge")}><Check /> Acquitter</button>}
              {editable && alert.status !== "resolved" && <button onClick={() => action(alert.id,"resolve")}>Résoudre</button>}
            </div>
          ))}
          {!alerts.length && <div className="empty">Aucune alerte {labels[status].toLowerCase()}.</div>}
        </div>
      </article>
    </Layout>
  );
}
