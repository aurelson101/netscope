import { FormEvent, useEffect, useState } from "react";
import { Play, ScanSearch, Trash2 } from "lucide-react";
import { api } from "../lib/api";
import { Layout } from "../components/Layout";
export function Scans() {
  const [scans, setScans] = useState<any[]>([]),
    [profiles, setProfiles] = useState<any[]>([]),
    [credentials, setCredentials] = useState<any[]>([]),
    [schedules, setSchedules] = useState<any[]>([]),
    [diagnostic, setDiagnostic] = useState<any>(),
    [error, setError] = useState("");
  const load = () => {
    api<any[]>("/scans").then(setScans);
    api<any[]>("/scan-profiles").then(setProfiles);
    api<any[]>("/credentials")
      .then(setCredentials)
      .catch(() => setCredentials([]));
    api<any[]>("/scan-schedules").then(setSchedules);
  };
  useEffect(load, []);
  async function submit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const f = new FormData(e.currentTarget);
    try {
      await api("/scans", {
        method: "POST",
        body: JSON.stringify({
          target: f.get("target"),
          profile_id: f.get("profile_id"),
          credential_id: f.get("credential_id") || null,
        }),
      });
      setError("");
      load();
    } catch (x: any) {
      setError(x.message);
    }
  }
  async function schedule(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const f = new FormData(e.currentTarget);
    try {
      await api("/scan-schedules", {
        method: "POST",
        body: JSON.stringify({
          name: f.get("name"),
          target: f.get("target"),
          profile_id: f.get("profile_id"),
          credential_id: f.get("credential_id") || null,
          interval_minutes: Number(f.get("interval_minutes")),
          enabled: true,
        }),
      });
      e.currentTarget.reset();
      load();
    } catch (x: any) {
      setError(x.message);
    }
  }
  async function snmp(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const f = new FormData(e.currentTarget);
    setDiagnostic(undefined);
    setDiagnostic(
      await api("/snmp/test", {
        method: "POST",
        body: JSON.stringify({
          target: f.get("target"),
          credential_id: f.get("credential_id") || null,
          oids: String(f.get("oids"))
            .split(",")
            .map((x) => x.trim())
            .filter(Boolean),
        }),
      }),
    );
  }
  async function remove(id: string) {
    await api("/scan-schedules/" + id, { method: "DELETE" });
    load();
  }
  async function toggle(row: any) {
    try {
      await api("/scan-schedules/" + row.id, {
        method: "PATCH",
        body: JSON.stringify({ enabled: !row.enabled }),
      });
      load();
    } catch (x: any) {
      setError(x.message);
    }
  }
  return (
    <Layout title="Scans de découverte">
      <div className="split">
        <article className="panel formPanel">
          <h3>Nouveau scan</h3>
          <form onSubmit={submit}>
            <TargetFields profiles={profiles} credentials={credentials} />
            {error && <div className="error">{error}</div>}
            <button className="primary">
              <Play />
              Lancer le scan
            </button>
          </form>
        </article>
        <article className="panel">
          <h3>Historique</h3>
          <div className="scanList">
            {scans.map((s) => (
              <div key={s.id}>
                <ScanSearch />
                <span>
                  <b>{s.target}</b>
                  <small>
                    {new Date(s.created_at).toLocaleString("fr")}
                    {s.error ? " · " + s.error : ""}
                  </small>
                </span>
                <em className={"badge " + s.status}>{s.status}</em>
              </div>
            ))}
          </div>
        </article>
      </div>
      <div className="split" style={{ marginTop: 12 }}>
        <article className="panel formPanel">
          <h3>Planifier un scan</h3>
          <form onSubmit={schedule}>
            <label>
              Nom
              <input name="name" required />
            </label>
            <TargetFields profiles={profiles} credentials={credentials} />
            <label>
              Fréquence
              <select name="interval_minutes" defaultValue="1440">
                <option value="60">Chaque heure</option>
                <option value="1440">Chaque jour</option>
                <option value="10080">Chaque semaine</option>
              </select>
            </label>
            <button className="primary">Enregistrer</button>
          </form>
          {schedules.map((x) => (
            <div className="rowActions" key={x.id}>
              <span>
                <b>{x.name}</b> · {x.target} · {x.interval_minutes} min ·{" "}
                {x.enabled ? "actif" : "suspendu"}
              </span>
              <button onClick={() => toggle(x)}>
                {x.enabled ? "Suspendre" : "Activer"}
              </button>
              <button className="danger" onClick={() => remove(x.id)}>
                <Trash2 />
              </button>
            </div>
          ))}
        </article>
        <article className="panel formPanel">
          <h3>Diagnostic SNMP / OID</h3>
          <form onSubmit={snmp}>
            <label>
              Équipement
              <input name="target" placeholder="192.168.1.1" required />
            </label>
            <label>
              Identifiant
              <select name="credential_id">
                <option value="">Défaut</option>
                {credentials.map((c) => (
                  <option key={c.id} value={c.id}>
                    {c.name}
                  </option>
                ))}
              </select>
            </label>
            <label>
              OID séparés par des virgules
              <input
                name="oids"
                defaultValue="1.3.6.1.2.1.1.1.0, 1.3.6.1.2.1.1.2.0, 1.3.6.1.2.1.1.5.0"
              />
            </label>
            <button className="primary">Tester</button>
          </form>
          {diagnostic && (
            <div className={diagnostic.success ? "hint" : "error"}>
              {diagnostic.success
                ? `Réponse en ${diagnostic.latency_ms} ms · sysObjectID ${diagnostic.sys_object_id || "inconnu"}`
                : diagnostic.error}
              {diagnostic.diagnostics?.map((x: any) => (
                <div key={x.oid}>
                  <code>{x.oid}</code> — {x.message}
                </div>
              ))}
            </div>
          )}
        </article>
      </div>
    </Layout>
  );
}
function TargetFields({
  profiles,
  credentials,
}: {
  profiles: any[];
  credentials: any[];
}) {
  return (
    <>
      <label>
        Cible
        <input name="target" placeholder="10.0.10.0/24" required />
      </label>
      <label>
        Profil
        <select name="profile_id" required>
          {profiles.map((p) => (
            <option key={p.id} value={p.id}>
              {p.name}
            </option>
          ))}
        </select>
      </label>
      <label>
        Identifiant SNMP
        <select name="credential_id">
          <option value="">Aucun / défaut</option>
          {credentials.map((c) => (
            <option key={c.id} value={c.id}>
              {c.name}
            </option>
          ))}
        </select>
      </label>
    </>
  );
}
