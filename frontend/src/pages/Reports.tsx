import { FormEvent, useEffect, useState } from "react";
import { Download, FileText, Mail, Send, Trash2 } from "lucide-react";
import { api, token } from "../lib/api";
import { Layout } from "../components/Layout";
export function Reports() {
  const [options, setOptions] = useState<any[]>([]),
    [smtp, setSmtp] = useState<any>({ configured: false, senders: [] }),
    [schedules, setSchedules] = useState<any[]>([]),
    [message, setMessage] = useState("");
  const load = () => {
    api<any[]>("/reports/options").then(setOptions);
    api("/smtp/status")
      .then(setSmtp)
      .catch(() => setSmtp({ configured: false, senders: [] }));
    api<any[]>("/report-schedules")
      .then(setSchedules)
      .catch(() => setSchedules([]));
  };
  useEffect(load, []);
  async function send(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const f = new FormData(e.currentTarget),
      recipients = String(f.get("recipients"))
        .split(",")
        .map((x) => x.trim())
        .filter(Boolean);
    try {
      const result: any = await api("/reports/email", {
        method: "POST",
        body: JSON.stringify({
          report_type: f.get("report_type"),
          format: f.get("format"),
          sender: f.get("sender"),
          recipients,
          subject: f.get("subject") || null,
          message: f.get("message") || null,
        }),
      });
      setMessage(`Rapport envoyé à ${result.recipients.join(", ")}`);
    } catch (x: any) {
      setMessage(x.message);
    }
  }
  async function schedule(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const form = e.currentTarget,
      f = new FormData(form);
    try {
      await api("/report-schedules", {
        method: "POST",
        body: JSON.stringify({
          name: f.get("name"),
          report_type: f.get("report_type"),
          format: f.get("format"),
          sender: f.get("sender"),
          recipients: String(f.get("recipients"))
            .split(",")
            .map((x) => x.trim())
            .filter(Boolean),
          interval_minutes: Number(f.get("interval_minutes")),
          enabled: true,
        }),
      });
      form.reset();
      load();
    } catch (x: any) {
      setMessage(x.message);
    }
  }
  async function remove(id: string) {
    await api("/report-schedules/" + id, { method: "DELETE" });
    load();
  }
  async function toggle(row: any) {
    try {
      await api("/report-schedules/" + row.id, {
        method: "PATCH",
        body: JSON.stringify({ enabled: !row.enabled }),
      });
      load();
    } catch (x: any) {
      setMessage(x.message);
    }
  }
  async function download(kind: string, format: string) {
    const r = await fetch(`/api/v1/reports/${kind}.${format}`, {
        headers: { Authorization: `Bearer ${token()}` },
      }),
      blob = await r.blob(),
      url = URL.createObjectURL(blob),
      a = document.createElement("a");
    a.href = url;
    a.download = `netscope-${kind}.${format}`;
    a.click();
    URL.revokeObjectURL(url);
  }
  return (
    <Layout title="Rapports">
      <div className="metrics">
        <article className="metric">
          <div>
            <span>Types</span>
            <strong>{options.length}</strong>
            <small>CSV et PDF</small>
          </div>
          <i className="blue">
            <FileText />
          </i>
        </article>
        <article className="metric">
          <div>
            <span>SMTP</span>
            <strong>{smtp.configured ? "Actif" : "Inactif"}</strong>
            <small>{smtp.host || "À configurer"}</small>
          </div>
          <i className={smtp.configured ? "green" : "red"}>
            <Mail />
          </i>
        </article>
      </div>
      <div className="split">
        <article className="panel formPanel">
          <h3>
            <Send /> Envoyer maintenant
          </h3>
          <ReportForm options={options} smtp={smtp} action={send} />
          {message && <div className="hint">{message}</div>}
        </article>
        <article className="panel">
          <h3>Téléchargements</h3>
          {options.map((x) => (
            <div className="rowActions" key={x.id}>
              <b>{x.label}</b>
              <button onClick={() => download(x.id, "csv")}>
                <Download />
                CSV
              </button>
              <button onClick={() => download(x.id, "pdf")}>
                <Download />
                PDF
              </button>
            </div>
          ))}
        </article>
      </div>
      <div className="split" style={{ marginTop: 12 }}>
        <article className="panel formPanel">
          <h3>Planifier un envoi</h3>
          <form onSubmit={schedule}>
            <label>
              Nom
              <input name="name" required />
            </label>
            <ReportFields options={options} smtp={smtp} />
            <label>
              Fréquence
              <select name="interval_minutes" defaultValue="10080">
                <option value="1440">Chaque jour</option>
                <option value="10080">Chaque semaine</option>
                <option value="43200">Chaque mois (30 jours)</option>
              </select>
            </label>
            <button className="primary" disabled={!smtp.configured}>
              Planifier
            </button>
          </form>
        </article>
        <article className="panel">
          <h3>Envois planifiés</h3>
          {schedules.map((x) => (
            <div className="rowActions" key={x.id}>
              <span>
                <b>{x.name}</b> · {x.report_type} · {x.interval_minutes} min ·{" "}
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
      </div>
    </Layout>
  );
}
function ReportFields({ options, smtp }: { options: any[]; smtp: any }) {
  return (
    <>
      <label>
        Rapport
        <select name="report_type" required>
          {options.map((x) => (
            <option key={x.id} value={x.id}>
              {x.label}
            </option>
          ))}
        </select>
      </label>
      <label>
        Format
        <select name="format">
          <option value="pdf">PDF</option>
          <option value="csv">CSV</option>
        </select>
      </label>
      <label>
        Expéditeur
        <select name="sender" required>
          <option value="">Choisir…</option>
          {smtp.senders?.map((x: string) => (
            <option key={x}>{x}</option>
          ))}
        </select>
      </label>
      <label>
        Destinataires
        <input
          name="recipients"
          required
          placeholder="admin@example.com, direction@example.com"
        />
      </label>
    </>
  );
}
function ReportForm({
  options,
  smtp,
  action,
}: {
  options: any[];
  smtp: any;
  action: (e: FormEvent<HTMLFormElement>) => void;
}) {
  return (
    <form onSubmit={action}>
      <ReportFields options={options} smtp={smtp} />
      <label>
        Sujet
        <input name="subject" />
      </label>
      <label>
        Message
        <input name="message" />
      </label>
      <button className="primary" disabled={!smtp.configured}>
        <Send />
        Générer et envoyer
      </button>
    </form>
  );
}
