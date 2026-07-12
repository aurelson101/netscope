import { FormEvent, useEffect, useState } from "react";
import { Network, Plus, Trash2 } from "lucide-react";
import { api } from "../lib/api";
import { Layout } from "../components/Layout";
import { canOperate, isAdmin, useCurrentUser } from "../lib/permissions";
export function Ipam() {
  const user = useCurrentUser(),
    editable = canOperate(user),
    administrative = isAdmin(user);
  const [prefixes, setPrefixes] = useState<any[]>([]),
    [addresses, setAddresses] = useState<any[]>([]),
    [error, setError] = useState("");
  const load = () => {
    api<any[]>("/ipam/prefixes").then(setPrefixes);
    api<any[]>("/ipam/addresses").then(setAddresses);
  };
  useEffect(load, []);
  async function addPrefix(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const form = e.currentTarget;
    const f = new FormData(form);
    try {
      await api("/ipam/prefixes", {
        method: "POST",
        body: JSON.stringify({
          prefix: f.get("prefix"),
          name: f.get("name"),
          status: "active",
          role: f.get("role") || null,
        }),
      });
      setError("");
      form.reset();
      load();
    } catch (x: any) {
      setError(x.message);
    }
  }
  async function removeAddress(a: any) {
    if (
      !confirm(
        `Retirer ${a.address} de l'IPAM ? L'équipement découvert restera dans l'inventaire.`,
      )
    )
      return;
    try {
      await api("/ipam/addresses/" + a.id, { method: "DELETE" });
      setError("");
      load();
    } catch (x: any) {
      setError(x.message);
    }
  }
  async function removePrefix(p: any) {
    const linked = addresses.filter((a) => a.prefix_id === p.id);
    if (
      !confirm(
        `Supprimer le préfixe ${p.prefix} ?${linked.length ? `\n\nVous devez d'abord retirer ses ${linked.length} adresse(s) IPAM.` : ""}`,
      )
    )
      return;
    try {
      await api("/ipam/prefixes/" + p.id, { method: "DELETE" });
      setError("");
      load();
    } catch (x: any) {
      setError(x.message);
    }
  }
  return (
    <Layout title="IPAM">
      <div className="metrics">
        <article className="metric">
          <div>
            <span>Préfixes</span>
            <strong>{prefixes.length}</strong>
            <small>IPv4 / IPv6</small>
          </div>
          <i className="blue">
            <Network />
          </i>
        </article>
        <article className="metric">
          <div>
            <span>Adresses enregistrées</span>
            <strong>{addresses.length}</strong>
            <small>Manuelles et découvertes</small>
          </div>
          <i className="green">
            <Network />
          </i>
        </article>
      </div>
      <div className="split">
        {editable && (
          <article className="panel formPanel">
            <h3>
              <Plus /> Ajouter un préfixe
            </h3>
            <form onSubmit={addPrefix}>
              <label>
                Préfixe
                <input name="prefix" placeholder="192.168.10.0/24" required />
              </label>
              <label>
                Nom
                <input name="name" placeholder="Utilisateurs Paris" required />
              </label>
              <label>
                Rôle
                <input
                  name="role"
                  placeholder="Utilisateurs, serveurs, management…"
                />
              </label>
              {error && <div className="error">{error}</div>}
              <button className="primary">Enregistrer</button>
            </form>
          </article>
        )}
        <article className="panel tablePanel">
          <table>
            <thead>
              <tr>
                <th>Préfixe</th>
                <th>Nom</th>
                <th>Rôle</th>
                <th>Utilisation</th>
                <th>Statut</th>
                {administrative && <th>Actions</th>}
              </tr>
            </thead>
            <tbody>
              {prefixes.map((p) => (
                <tr key={p.id}>
                  <td className="mono">{p.prefix}</td>
                  <td>{p.name}</td>
                  <td>{p.role || "—"}</td>
                  <td>
                    <span className="confidence">
                      {p.used} / {p.used + p.available} · {p.utilization}%
                    </span>
                  </td>
                  {administrative && (
                    <td>
                      <span className={"badge " + p.status}>{p.status}</span>
                    </td>
                  )}
                  <td>
                    <div className="rowActions">
                      <button
                        className="danger"
                        onClick={() => removePrefix(p)}
                        title="Supprimer le préfixe"
                      >
                        <Trash2 />
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          {!prefixes.length && <div className="empty">Aucun préfixe IPAM</div>}
        </article>
      </div>
      <article className="panel tablePanel" style={{ marginTop: 12 }}>
        <table>
          <thead>
            <tr>
              <th>Adresse</th>
              <th>DNS</th>
              <th>Rôle</th>
              <th>Source</th>
              <th>Statut</th>
              <th>Dernière observation</th>
              {editable && <th>Actions</th>}
            </tr>
          </thead>
          <tbody>
            {addresses.map((a) => (
              <tr
                key={a.id}
                onClick={() =>
                  a.asset_id && (location.hash = "#/assets/" + a.asset_id)
                }
              >
                <td className="mono">{a.address}</td>
                <td>{a.dns_name || "—"}</td>
                <td>{a.role || "—"}</td>
                <td>
                  <span className="tag">{a.source}</span>
                </td>
                {editable && (
                  <td>
                    <span className={"dot " + a.status}></span>
                    {a.status}
                  </td>
                )}
                <td>
                  {a.last_seen
                    ? new Date(a.last_seen).toLocaleString("fr")
                    : "—"}
                </td>
                <td>
                  <div className="rowActions">
                    <button
                      className="danger"
                      title="Retirer de l'IPAM"
                      onClick={(e) => {
                        e.stopPropagation();
                        removeAddress(a);
                      }}
                    >
                      <Trash2 />
                    </button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </article>
    </Layout>
  );
}
