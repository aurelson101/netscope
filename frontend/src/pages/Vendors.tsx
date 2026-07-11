import { useEffect, useMemo, useState } from "react";
import {
  Box,
  Camera,
  Flame,
  HardDrive,
  Monitor,
  Printer,
  Router,
  Server,
  Smartphone,
  Wifi,
} from "lucide-react";
import { api } from "../lib/api";
import { Layout } from "../components/Layout";
const categories = [
  ["all", "Tous", Box],
  ["phone", "Smartphones", Smartphone],
  ["switch", "Commutateurs", Router],
  ["server", "Serveurs", Server],
  ["workstation", "Postes de travail", Monitor],
  ["laptop", "Ordinateurs portables", Monitor],
  ["printer", "Imprimantes", Printer],
  ["router", "Routeurs", Router],
  ["firewall", "Pare-feu", Flame],
  ["wireless access point", "Points d’accès Wi-Fi", Wifi],
  ["camera", "Caméras", Camera],
  ["storage", "Stockage", HardDrive],
  ["NAS", "NAS", HardDrive],
  ["unknown", "Non classés", Box],
] as const;
export function Vendors() {
  const [rows, setRows] = useState<any[]>([]),
    [category, setCategory] = useState("all");
  useEffect(() => {
    api<any[]>("/vendors").then(setRows);
  }, []);
  const visible = useMemo(
    () =>
      category === "all"
        ? rows
        : rows.filter((v) => v.device_types?.includes(category)),
    [rows, category],
  );
  const count = (type: string) =>
    type === "all"
      ? rows.reduce((n, v) => n + v.assets, 0)
      : rows.reduce((n, v) => n + (v.device_type_counts?.[type] || 0), 0);
  return (
    <Layout title="Constructeurs">
      <div className="vendorCategories">
        {categories.map(([type, label, Icon]) => (
          <button
            key={type}
            className={category === type ? "active" : ""}
            onClick={() => setCategory(type)}
          >
            <Icon />
            <span>{label}</span>
            <b>{count(type)}</b>
          </button>
        ))}
      </div>
      <article className="panel tablePanel">
        <table>
          <thead>
            <tr>
              <th>Constructeur normalisé</th>
              <th>Catégories détectées</th>
              <th>Actifs</th>
              <th>Action</th>
            </tr>
          </thead>
          <tbody>
            {visible.map((v) => (
              <tr
                key={v.name}
                onClick={() => {
                  const p = new URLSearchParams({ manufacturer: v.name });
                  if (category !== "all") p.set("device_type", category);
                  location.hash = "#/assets?" + p;
                }}
              >
                <td>
                  <Box /> {v.name}
                </td>
                <td>
                  {v.device_types?.length ? (
                    v.device_types.map((x: string) => (
                      <span className="tag vendorTag" key={x}>
                        {categories.find((c) => c[0] === x)?.[1] || x}
                      </span>
                    ))
                  ) : (
                    <span className="hint">Catalogue mobile</span>
                  )}
                </td>
                <td>{v.assets}</td>
                <td>{v.assets ? "Voir les actifs" : "Aucun détecté"}</td>
              </tr>
            ))}
          </tbody>
        </table>
        {!visible.length && (
          <div className="empty">Aucun constructeur dans cette catégorie</div>
        )}
      </article>
    </Layout>
  );
}
