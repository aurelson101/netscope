import { FormEvent, useEffect, useState } from "react";
import { Play, ScanSearch, Trash2 } from "lucide-react";
import { api } from "../lib/api";
import { Layout } from "../components/Layout";
import { canOperate, useCurrentUser } from "../lib/permissions";
export function Scans() {
  const editable = canOperate(useCurrentUser());
  const [scans, setScans] = useState<any[]>([]),
    [profiles, setProfiles] = useState<any[]>([]),
    [credentials, setCredentials] = useState<any[]>([]),
    [vrfs, setVrfs] = useState<any[]>([]),
    [schedules, setSchedules] = useState<any[]>([]),
    [diagnostic, setDiagnostic] = useState<any>(),
    [error, setError] = useState("");
  const load = () => {
    api<any[]>("/scans")
      .then(setScans)
      .catch((x) => setError(x.message));
    api<any[]>("/scan-profiles")
      .then(setProfiles)
      .catch((x) => setError(x.message));
    api<any[]>("/credentials")
      .then(setCredentials)
      .catch(() => setCredentials([]));
    api<any[]>("/scan-schedules")
      .then(setSchedules)
      .catch((x) => setError(x.message));
    api<any[]>("/ipam/vrfs").then(setVrfs).catch(() => setVrfs([]));
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
          vrf_id: f.get("vrf_id") || null,
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
    const form = e.currentTarget,
      f = new FormData(form);
    try {
      await api("/scan-schedules", {
        method: "POST",
        body: JSON.stringify({
          name: f.get("name"),
          target: f.get("target"),
          profile_id: f.get("profile_id"),
          credential_id: f.get("credential_id") || null,
          vrf_id: f.get("vrf_id") || null,
          interval_minutes: Number(f.get("interval_minutes")),
          enabled: true,
        }),
      });
      form.reset();
      load();
    } catch (x: any) {
      setError(x.message);
    }
  }
  async function snmp(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const f = new FormData(e.currentTarget);
    setDiagnostic(undefined);
    try {
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
      setError("");
    } catch (x: any) {
      setError(x.message);
    }
  }
  async function remove(id: string) {
    try {
      await api("/scan-schedules/" + id, { method: "DELETE" });
      setError("");
      load();
    } catch (x: any) {
      setError(x.message);
    }
  }
  async function removeScan(scan: any) {
    if (!confirm(`Supprimer le scan de ${scan.target} de l’historique ?`))
      return;
    try {
      await api("/scans/" + scan.id, { method: "DELETE" });
      setError("");
      load();
    } catch (x: any) {
      setError(x.message);
    }
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
      {error && <div className="error">{error}</div>}
      <div className="split">
        <article className="panel formPanel">
          <h3>Nouveau scan</h3>
          {editable ? (
            <form onSubmit={submit}>
              <TargetFields profiles={profiles} credentials={credentials} vrfs={vrfs} />
              <button className="primary">
                <Play />
                Lancer le scan
              </button>
            </form>
          ) : (
            <p className="readOnlyNotice">
              Mode lecture : le lancement de scans est réservé aux opérateurs.
            </p>
          )}
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
                {editable && !["queued", "running"].includes(s.status) && (
                  <button
                    className="icon danger"
                    title="Supprimer de l’historique"
                    onClick={() => removeScan(s)}
                  >
                    <Trash2 />
                  </button>
                )}
              </div>
            ))}
          </div>
        </article>
      </div>
      <div className="split" style={{ marginTop: 12 }}>
        <article className="panel formPanel">
          <h3>Planifier un scan</h3>
          {editable && (
            <form onSubmit={schedule}>
              <label>
                Nom
                <input name="name" required />
              </label>
              <TargetFields profiles={profiles} credentials={credentials} vrfs={vrfs} />
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
          )}
          {schedules.map((x) => (
            <div className="rowActions" key={x.id}>
              <span>
                <b>{x.name}</b> · {x.target} · {x.interval_minutes} min ·{" "}
                {x.enabled ? "actif" : "suspendu"}
              </span>
              {editable && (
                <button onClick={() => toggle(x)}>
                  {x.enabled ? "Suspendre" : "Activer"}
                </button>
              )}
              {editable && (
                <button className="danger" onClick={() => remove(x.id)}>
                  <Trash2 />
                </button>
              )}
            </div>
          ))}
        </article>
        <article className="panel formPanel">
          <h3>Diagnostic SNMP / OID</h3>
          {editable ? (
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
          ) : (
            <p className="readOnlyNotice">
              Le diagnostic actif SNMP nécessite le rôle opérateur.
            </p>
          )}
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
  vrfs,
}: {
  profiles: any[];
  credentials: any[];
  vrfs: any[];
}) {
  return (
    <>
      <label>
        Cible
        <input name="target" placeholder="10.0.10.0/24" required />
      </label>
      <label>
        VRF
        <select name="vrf_id">
          <option value="">Globale</option>
          {vrfs.map((vrf) => <option value={vrf.id} key={vrf.id}>{vrf.name}</option>)}
        </select>
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
