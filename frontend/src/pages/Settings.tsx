import { FormEvent, useEffect, useState } from "react";
import {
  Download,
  HardDrive,
  HeartPulse,
  KeyRound,
  LockKeyhole,
  RefreshCw,
  Save,
  ServerCog,
  ShieldCheck,
} from "lucide-react";
import { api, downloadFile } from "../lib/api";
import { Layout } from "../components/Layout";
import { canOperate, isAdmin, useCurrentUser } from "../lib/permissions";
export function Settings() {
  const user = useCurrentUser(),
    editable = canOperate(user),
    administrative = isAdmin(user);
  const [prefixes, setPrefixes] = useState<any[]>([]),
    [mfa, setMfa] = useState<any>({ enabled: false }),
    [setup, setSetup] = useState<any>(),
    [versions, setVersions] = useState<any[]>([]),
    [monitoring, setMonitoring] = useState<any>(),
    [monitoringLoading, setMonitoringLoading] = useState(false),
    [message, setMessage] = useState("");
  const load = () => {
    api<any[]>("/ipam/prefixes")
      .then(setPrefixes)
      .catch((x) => setMessage(x.message));
    api("/auth/mfa/status")
      .then(setMfa)
      .catch((x) => setMessage(x.message));
    api<any[]>("/configuration/versions")
      .then(setVersions)
      .catch(() => setVersions([]));
  };
  useEffect(load, []);
  async function loadMonitoring() {
    setMonitoringLoading(true);
    try {
      setMonitoring(await api("/system/monitoring"));
    } catch (x: any) {
      setMonitoring({
        status: "critical",
        monitor_available: false,
        containers: [],
        error: x.message,
      });
    } finally {
      setMonitoringLoading(false);
    }
  }
  useEffect(() => {
    if (!administrative) return;
    loadMonitoring();
    const timer = window.setInterval(loadMonitoring, 15000);
    return () => window.clearInterval(timer);
  }, [administrative]);
  async function saveDns(e: FormEvent<HTMLFormElement>, id: string) {
    e.preventDefault();
    const form = e.currentTarget;
    const f = new FormData(form),
      dns = String(f.get("dns"))
        .split(",")
        .map((x) => x.trim())
        .filter(Boolean);
    try {
      await api("/ipam/prefixes/" + id, {
        method: "PATCH",
        body: JSON.stringify({ dns_servers: dns }),
      });
      setMessage("Serveurs DNS enregistrés");
      load();
    } catch (x: any) {
      setMessage(x.message);
    }
  }
  async function testDns(e: React.MouseEvent<HTMLButtonElement>) {
    const form = e.currentTarget.form;
    if (!form) return;
    const f = new FormData(form),
      server = String(f.get("dns")).split(",")[0]?.trim(),
      ip = String(f.get("test_ip")).trim();
    if (!server || !ip) {
      setMessage("Renseignez un DNS et une IP à tester");
      return;
    }
    const result: any = await api("/dns/test", {
      method: "POST",
      body: JSON.stringify({ server, ip_address: ip }),
    });
    setMessage(
      result.success
        ? `DNS OK : ${result.names.join(", ")} (${result.latency_ms} ms)`
        : `Échec DNS : ${result.error}`,
    );
  }
  async function startMfa() {
    setSetup(await api("/auth/mfa/setup", { method: "POST" }));
  }
  async function confirm(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const f = new FormData(e.currentTarget);
    try {
      await api("/auth/mfa/confirm", {
        method: "POST",
        body: JSON.stringify({ code: f.get("code") }),
      });
      setSetup(undefined);
      setMessage("MFA activé");
      load();
    } catch (x: any) {
      setMessage(x.message);
    }
  }
  async function disable(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const f = new FormData(e.currentTarget);
    try {
      await api("/auth/mfa/disable", {
        method: "POST",
        body: JSON.stringify({ code: f.get("code") }),
      });
      setMessage("MFA désactivé");
      load();
    } catch (x: any) {
      setMessage(x.message);
    }
  }
  async function password(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const form = e.currentTarget;
    const f = new FormData(form),
      next = String(f.get("new_password")),
      confirm = String(f.get("confirm_password"));
    if (next !== confirm) {
      setMessage("La confirmation du mot de passe ne correspond pas");
      return;
    }
    try {
      await api("/auth/password", {
        method: "POST",
        body: JSON.stringify({
          current_password: f.get("current_password"),
          new_password: next,
        }),
      });
      form.reset();
      setMessage("Mot de passe modifié avec succès");
    } catch (x: any) {
      setMessage(x.message);
    }
  }
  async function snapshot(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const form = e.currentTarget,
      f = new FormData(form);
    try {
      await api("/configuration/versions", {
        method: "POST",
        body: JSON.stringify({ comment: f.get("comment") || null }),
      });
      form.reset();
      setMessage("Configuration versionnée");
      load();
    } catch (x: any) {
      setMessage(x.message);
    }
  }
  async function backup(id: string, version: number) {
    try {
      await downloadFile(
        `/configuration/versions/${id}/backup`,
        `netscope-config-v${version}.json`,
      );
      setMessage("");
    } catch (x: any) {
      setMessage(x.message);
    }
  }
  return (
    <Layout title="Paramètres">
      <div className="settingsGrid">
        {administrative && (
          <article className="panel monitoringPanel">
            <div className="monitoringHeader">
              <h3>
                <HeartPulse /> Supervision de la plateforme
              </h3>
              <div className="monitoringActions">
                <span
                  className={`monitoringState ${monitoring?.status === "healthy" ? "healthy" : "critical"}`}
                >
                  <i />
                  {monitoring?.status === "healthy"
                    ? "Tous les services sont opérationnels"
                    : "Attention requise"}
                </span>
                <button
                  className="icon"
                  onClick={loadMonitoring}
                  disabled={monitoringLoading}
                  title="Actualiser"
                >
                  <RefreshCw className={monitoringLoading ? "spinning" : ""} />
                </button>
              </div>
            </div>
            {monitoring?.error && (
              <p className="monitoringError">{monitoring.error}</p>
            )}
            <div className="monitoringSummary">
              <div>
                <HardDrive />
                <span>
                  <small>Espace disque disponible</small>
                  <b>
                    {monitoring?.disk
                      ? `${formatBytes(monitoring.disk.free_bytes)} (${monitoring.disk.free_percent} %)`
                      : "—"}
                  </b>
                </span>
              </div>
              <div className="diskBar" aria-label="Utilisation du disque">
                <i
                  className={monitoring?.disk?.used_percent >= 90 ? "critical" : ""}
                  style={{ width: `${monitoring?.disk?.used_percent || 0}%` }}
                />
              </div>
            </div>
            <div className="containerGrid">
              {(monitoring?.containers || []).map((container: any) => (
                <div
                  className={`containerHealth ${container.healthy ? "healthy" : "critical"}`}
                  key={container.name}
                >
                  <i />
                  <span>
                    <b>{container.service}</b>
                    <small>
                      {container.state} · health {container.health}
                      {container.restarts
                        ? ` · ${container.restarts} redémarrage(s)`
                        : ""}
                    </small>
                  </span>
                </div>
              ))}
              {monitoring && !monitoring.containers?.length && (
                <p className="hint">Aucun état de conteneur disponible.</p>
              )}
            </div>
            {monitoring?.checked_at && (
              <small className="monitoringTime">
                Dernière vérification : {new Date(monitoring.checked_at).toLocaleString("fr")}
              </small>
            )}
          </article>
        )}
        {editable && (
          <article className="panel formPanel">
            <h3>
              <ServerCog /> Résolution DNS
            </h3>
            <p className="hint">
              Configurez les serveurs PTR internes puis vérifiez-les avant un
              scan.
            </p>
            {prefixes.map((p) => (
              <form key={p.id} onSubmit={(e) => saveDns(e, p.id)}>
                <label>
                  {p.prefix} — {p.name}
                  <input
                    name="dns"
                    defaultValue={(p.dns_servers || []).join(", ")}
                    placeholder="192.168.1.254, 192.168.1.1"
                  />
                </label>
                <label>
                  IP à résoudre pour le test
                  <input name="test_ip" placeholder="192.168.1.95" />
                </label>
                <div className="formActions">
                  <button type="button" className="button" onClick={testDns}>
                    Tester le PTR
                  </button>
                  <button className="primary">Enregistrer</button>
                </div>
              </form>
            ))}
          </article>
        )}
        {administrative && (
          <article className="panel formPanel">
            <h3>
              <Save />
              Versions de configuration
            </h3>
            <form onSubmit={snapshot}>
              <label>
                Commentaire
                <input name="comment" placeholder="Avant changement réseau…" />
              </label>
              <button className="primary">Créer un instantané</button>
            </form>
            {versions.map((v) => (
              <div className="rowActions" key={v.id}>
                <span>
                  <b>v{v.version}</b> ·{" "}
                  {v.comment || new Date(v.created_at).toLocaleString("fr")}
                </span>
                <button onClick={() => backup(v.id, v.version)}>
                  <Download />
                  Sauvegarder
                </button>
              </div>
            ))}
          </article>
        )}
        {editable && (
          <article className="panel formPanel">
            <h3>
              <ShieldCheck /> Authentification multifacteur
            </h3>
            <p className="hint">
              État : <b>{mfa.enabled ? "Activé" : "Désactivé"}</b>.
            </p>
            {!mfa.enabled && !setup && (
              <button className="primary" onClick={startMfa}>
                <KeyRound />
                Configurer le MFA
              </button>
            )}
            {setup && (
              <>
                <div className="mfaSecret">
                  <small>Clé à saisir dans l’application</small>
                  <code>{setup.secret}</code>
                  <small>{setup.otpauth_uri}</small>
                </div>
                <CodeForm action={confirm} label="Confirmer et activer" />
              </>
            )}
            {mfa.enabled && (
              <CodeForm action={disable} label="Désactiver le MFA" />
            )}
          </article>
        )}
        {editable && (
          <article className="panel formPanel">
            <h3>
              <LockKeyhole /> Mot de passe
            </h3>
            <p className="hint">
              12 caractères minimum avec majuscule, minuscule, chiffre et
              caractère spécial.
            </p>
            <form onSubmit={password}>
              <label>
                Mot de passe actuel
                <input
                  name="current_password"
                  type="password"
                  autoComplete="current-password"
                  required
                />
              </label>
              <label>
                Nouveau mot de passe
                <input
                  name="new_password"
                  type="password"
                  minLength={12}
                  autoComplete="new-password"
                  required
                />
              </label>
              <label>
                Confirmation
                <input
                  name="confirm_password"
                  type="password"
                  minLength={12}
                  autoComplete="new-password"
                  required
                />
              </label>
              <button className="primary">Changer le mot de passe</button>
            </form>
          </article>
        )}
        {!editable && (
          <article className="panel">
            <p className="readOnlyNotice">
              Mode affichage : aucune configuration du compte n’est autorisée.
            </p>
          </article>
        )}
      </div>
      {message && (
        <div className="panel" style={{ marginTop: 12 }}>
          {message}
        </div>
      )}
    </Layout>
  );
}
function formatBytes(value: number) {
  if (!Number.isFinite(value)) return "—";
  const units = ["o", "Kio", "Mio", "Gio", "Tio"];
  let amount = value,
    index = 0;
  while (amount >= 1024 && index < units.length - 1) {
    amount /= 1024;
    index++;
  }
  return `${amount.toFixed(index > 2 ? 1 : 0)} ${units[index]}`;
}
function CodeForm({
  action,
  label,
}: {
  action: (e: FormEvent<HTMLFormElement>) => void;
  label: string;
}) {
  return (
    <form onSubmit={action}>
      <label>
        Code à 6 chiffres
        <input
          name="code"
          inputMode="numeric"
          pattern="[0-9]{6}"
          maxLength={6}
          required
        />
      </label>
      <button className="primary">{label}</button>
    </form>
  );
}
