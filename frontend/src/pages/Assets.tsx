import { FormEvent, useEffect, useMemo, useState } from "react";
import {
  Download,
  Pencil,
  Plus,
  Search,
  Server,
  Trash2,
  X,
} from "lucide-react";
import { api, Asset, downloadAssets } from "../lib/api";
import { Layout } from "../components/Layout";
import { canOperate, useCurrentUser } from "../lib/permissions";
export function Assets() {
  const editable = canOperate(useCurrentUser());
  const initial = useMemo(
      () => new URLSearchParams(location.hash.split("?")[1] || ""),
      [],
    ),
    [rows, setRows] = useState<Asset[]>([]),
    [q, setQ] = useState(initial.get("search") || ""),
    [editor, setEditor] = useState<Asset | null | false>(false),
    [error, setError] = useState("");
  const filters = useMemo(
    () => Object.fromEntries(initial.entries()),
    [initial],
  );
  const load = () => {
    const params = new URLSearchParams(filters);
    if (q) params.set("search", q);
    api<Asset[]>("/assets?" + params).then(setRows);
  };
  useEffect(() => {
    const timer = setTimeout(load, 200);
    return () => clearTimeout(timer);
  }, [q]);
  async function save(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const f = new FormData(e.currentTarget),
      editing = !!editor;
    const body: any = {
      hostname: f.get("hostname") || null,
      manufacturer: f.get("manufacturer") || null,
      model: f.get("model") || null,
      device_type: f.get("device_type") || "unknown",
      operating_system: f.get("operating_system") || null,
      role: f.get("role") || null,
      owner: f.get("owner") || null,
      criticality: f.get("criticality") || null,
      notes: f.get("notes") || null,
    };
    if (!editing) {
      body.ip_address = f.get("ip_address");
      body.mac_address = f.get("mac_address") || null;
    }
    try {
      await api(editing ? "/assets/" + editor.id : "/assets", {
        method: editing ? "PATCH" : "POST",
        body: JSON.stringify(body),
      });
      setEditor(false);
      setError("");
      load();
    } catch (x: any) {
      setError(x.message);
    }
  }
  async function remove(e: React.MouseEvent, asset: Asset) {
    e.stopPropagation();
    if (
      !confirm(
        `Archiver ${asset.hostname || asset.addresses[0]?.address || "cet actif"} ?`,
      )
    )
      return;
    const reason = prompt("Motif de l’archivage (facultatif)") || null;
    try {
      await api("/assets/" + asset.id, {
        method: "DELETE",
        body: JSON.stringify({ reason }),
      });
      load();
    } catch (x: any) {
      setError(x.message);
    }
  }
  async function exportAssets() {
    try {
      await downloadAssets();
      setError("");
    } catch (x: any) {
      setError(x.message);
    }
  }
  const labels: Record<string, string> = {
    status: "Statut",
    device_type: "Type",
    manufacturer: "Constructeur",
    operating_system: "Système",
    recent_hours: "Découverts depuis",
  };
  return (
    <Layout title="Inventaire des actifs">
      <div className="pageHead">
        <div className="search">
          <Search />
          <input
            placeholder="IP, nom d’hôte, constructeur…"
            value={q}
            onChange={(e) => setQ(e.target.value)}
          />
        </div>
        {editable && (
          <button className="button" onClick={() => setEditor(null)}>
            <Plus />
            Ajouter
          </button>
        )}
        {editable && (
          <button className="button" onClick={exportAssets}>
            <Download />
            Exporter CSV
          </button>
        )}
      </div>
      {Object.keys(filters).length > 0 && (
        <div className="filterBar">
          <span>Filtre actif :</span>
          {Object.entries(filters).map(([k, v]) => (
            <b key={k}>
              {labels[k] || k} : {k === "recent_hours" ? v + " h" : v}
            </b>
          ))}
          <button className="icon" onClick={() => (location.hash = "#/assets")}>
            <X />
            Effacer
          </button>
        </div>
      )}
      {error && <div className="error">{error}</div>}
      {editable && editor !== false && (
        <AssetEditor
          key={editor?.id || "new"}
          asset={editor}
          onSave={save}
          onClose={() => setEditor(false)}
        />
      )}
      <article className="panel tablePanel">
        <table>
          <thead>
            <tr>
              <th>Statut</th>
              <th>IP</th>
              <th>Nom d’hôte</th>
              <th>MAC</th>
              <th>Constructeur</th>
              <th>Type</th>
              <th>Système</th>
              <th>Dernier vu</th>
              <th>Confiance</th>
              {editable && <th>Actions</th>}
            </tr>
          </thead>
          <tbody>
            {rows.map((a) => (
              <tr
                key={a.id}
                onClick={() => (location.hash = "#/assets/" + a.id)}
              >
                <td>
                  <span className={"dot " + a.status}></span>
                  {a.status}
                </td>
                <td>{a.addresses[0]?.address || "—"}</td>
                <td>
                  <b>{a.hostname || "Inconnu"}</b>
                </td>
                <td className="mono">
                  {a.identifiers.find((x) => x.kind === "mac")?.value || "—"}
                </td>
                <td>{a.manufacturer || "—"}</td>
                <td>
                  <span className="tag">{a.device_type}</span>
                </td>
                <td>{a.operating_system || "—"}</td>
                <td>{new Date(a.last_seen).toLocaleString("fr")}</td>
                <td>
                  <span className="confidence">
                    {Math.round(a.confidence * 100)}%
                  </span>
                </td>
                {editable && (
                  <td>
                    <div className="rowActions">
                      <button
                        title="Modifier"
                        onClick={(e) => {
                          e.stopPropagation();
                          setEditor(a);
                        }}
                      >
                        <Pencil />
                      </button>
                      <button
                        title="Archiver"
                        className="danger"
                        onClick={(e) => remove(e, a)}
                      >
                        <Trash2 />
                      </button>
                    </div>
                  </td>
                )}
              </tr>
            ))}
          </tbody>
        </table>
        {!rows.length && (
          <div className="empty">
            <Server />
            <span>Aucun actif ne correspond à ce filtre.</span>
          </div>
        )}
      </article>
    </Layout>
  );
}
function AssetEditor({
  asset,
  onSave,
  onClose,
}: {
  asset: Asset | null;
  onSave: (e: FormEvent<HTMLFormElement>) => void;
  onClose: () => void;
}) {
  const [metadata, setMetadata] = useState<any>({});
  useEffect(() => {
    if (asset) api<any>(`/assets/${asset.id}/metadata`).then(setMetadata).catch(() => setMetadata({}));
    else setMetadata({});
  }, [asset?.id]);
  const mac = asset?.identifiers.find((x) => x.kind === "mac")?.value || "";
  return (
    <article className="panel assetEditor">
      <div className="editorHead">
        <h3>{asset ? "Modifier l’actif" : "Ajouter un actif manuellement"}</h3>
        <button className="icon" onClick={onClose}>
          <X />
        </button>
      </div>
      <form onSubmit={onSave}>
        {!asset && (
          <>
            <label>
              Adresse IP
              <input name="ip_address" placeholder="192.168.1.50" required />
            </label>
            <label>
              Adresse MAC
              <input name="mac_address" placeholder="AA:BB:CC:DD:EE:FF" />
            </label>
          </>
        )}
        {asset && <label>Adresse MAC<input name="mac_address" value={mac || "Non disponible"} readOnly /></label>}
        <label>
          Nom d’hôte
          <input name="hostname" defaultValue={asset?.hostname} />
        </label>
        <label>
          Constructeur
          <input name="manufacturer" defaultValue={asset?.manufacturer} />
        </label>
        <label>
          Modèle
          <input name="model" defaultValue={asset?.model} />
        </label>
        <label>
          Type
          <select
            name="device_type"
            defaultValue={asset?.device_type || "unknown"}
          >
            {[
              "unknown",
              "workstation",
              "laptop",
              "server",
              "virtual machine",
              "switch",
              "router",
              "firewall",
              "wireless access point",
              "printer",
              "camera",
              "phone",
              "IoT device",
              "storage",
              "NAS",
              "UPS",
            ].map((x) => (
              <option key={x}>{x}</option>
            ))}
          </select>
        </label>
        <label>
          Système
          <input
            name="operating_system"
            defaultValue={asset?.operating_system}
          />
        </label>
        <label>
          Rôle
          <input name="role" defaultValue={metadata.role || ""} />
        </label>
        <label>
          Propriétaire
          <input name="owner" defaultValue={metadata.owner || ""} />
        </label>
        <label>
          Criticité
          <select name="criticality" defaultValue={metadata.criticality || ""}>
            <option value="">Non définie</option>
            <option>low</option>
            <option>medium</option>
            <option>high</option>
            <option>critical</option>
          </select>
        </label>
        <label className="wide">
          Notes
          <input name="notes" defaultValue={metadata.notes || ""} />
        </label>
        <button className="primary wide">
          {asset ? "Enregistrer les modifications" : "Créer l’actif"}
        </button>
      </form>
    </article>
  );
}
