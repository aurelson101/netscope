import { useEffect, useState } from "react";
import {
  Activity,
  AlertTriangle,
  Clock,
  HelpCircle,
  Monitor,
  Radio,
  Server,
} from "lucide-react";
import {
  Bar,
  BarChart,
  Cell,
  Legend,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { api, downloadAssets } from "../lib/api";
import { Layout } from "../components/Layout";
import { canOperate, useCurrentUser } from "../lib/permissions";
const colors = [
  "#408cff",
  "#35c979",
  "#f1ad38",
  "#a879e8",
  "#ef6253",
  "#5d7ca8",
];
const go = (params: Record<string, string | number>) => {
  location.hash =
    "#/assets?" +
    new URLSearchParams(
      Object.entries(params).map(([k, v]) => [k, String(v)]),
    ).toString();
};
export function Dashboard() {
  const editable = canOperate(useCurrentUser());
  const [d, setD] = useState<any>(),
    [error, setError] = useState("");
  useEffect(() => {
    api("/dashboard")
      .then(setD)
      .catch((x) => setError(x.message));
  }, []);
  if (error)
    return (
      <Layout title="Tableau de bord">
        <div className="error">Chargement impossible : {error}</div>
      </Layout>
    );
  if (!d)
    return (
      <Layout title="Tableau de bord">
        <div className="loading">Chargement…</div>
      </Layout>
    );
  const cards = [
    ["Actifs totaux", d.total, Server, "blue", {}],
    ["En ligne", d.online, Activity, "green", { status: "online" }],
    ["Hors ligne", d.offline, Monitor, "red", { status: "offline" }],
    ["Nouveaux actifs", d.new_24h, Radio, "purple", { recent_hours: 24 }],
    ["Inconnus", d.unknown, HelpCircle, "yellow", { status: "unknown" }],
  ];
  return (
    <Layout title="Tableau de bord">
      <div className="toolbar">
        <button>Dernières 24 heures</button>
        {editable && (
          <button className="button" onClick={downloadAssets}>
            Exporter
          </button>
        )}
      </div>
      <div className="metrics">
        {cards.map(([l, v, I, c, filter]: any) => (
          <article
            key={l}
            className="metric clickable"
            onClick={() => go(filter)}
            title={"Afficher : " + l}
          >
            <div>
              <span>{l}</span>
              <strong>{v.toLocaleString("fr-FR")}</strong>
              <small>Cliquer pour ouvrir l’inventaire</small>
            </div>
            <i className={c}>
              <I />
            </i>
          </article>
        ))}
      </div>
      <div className="charts">
        <Panel title="Actifs par type d’équipement" className="donutPanel">
          {d.by_type.length ? (
            <div className="chartFrame donutFrame">
              <ResponsiveContainer width="100%" height={280}>
                <PieChart>
                  <Pie
                    className="chartClick"
                    data={d.by_type}
                    dataKey="value"
                    nameKey="label"
                    cx="50%"
                    cy="43%"
                    innerRadius={58}
                    outerRadius={88}
                    paddingAngle={2}
                    stroke="transparent"
                    onClick={(x: any) => go({ device_type: x.label })}
                  >
                    {d.by_type.map((_: any, i: number) => (
                      <Cell key={i} fill={colors[i % colors.length]} />
                    ))}
                  </Pie>
                  <Tooltip
                    contentStyle={{
                      background: "#0b1d2b",
                      border: "1px solid #31516a",
                      borderRadius: 8,
                    }}
                    itemStyle={{ color: "#e8f2fb" }}
                  />
                  <Legend
                    onClick={(x: any) => go({ device_type: x.value })}
                    layout="horizontal"
                    verticalAlign="bottom"
                    align="center"
                    iconType="circle"
                  />
                </PieChart>
              </ResponsiveContainer>
              <div className="donutTotal">
                <strong>{d.total.toLocaleString("fr-FR")}</strong>
                <span>actifs</span>
              </div>
            </div>
          ) : (
            <Empty text="Aucune donnée de type" />
          )}
        </Panel>
        <Panel title="Actifs par constructeur">
          <ResponsiveContainer width="100%" height={250}>
            <BarChart
              data={d.by_vendor}
              layout="vertical"
              onClick={(x: any) =>
                x?.activePayload?.[0] &&
                go({ manufacturer: x.activePayload[0].payload.label })
              }
            >
              <XAxis type="number" hide />
              <YAxis type="category" dataKey="label" width={90} />
              <Tooltip />
              <Bar
                className="chartClick"
                dataKey="value"
                fill="#467ec9"
                radius={3}
              />
            </BarChart>
          </ResponsiveContainer>
        </Panel>
        <Panel title="Actifs par système d’exploitation">
          <ResponsiveContainer width="100%" height={250}>
            <BarChart
              data={d.by_os}
              layout="vertical"
              onClick={(x: any) =>
                x?.activePayload?.[0] &&
                go({ operating_system: x.activePayload[0].payload.label })
              }
            >
              <XAxis type="number" hide />
              <YAxis type="category" dataKey="label" width={100} />
              <Tooltip />
              <Bar
                className="chartClick"
                dataKey="value"
                fill="#365f91"
                radius={3}
              />
            </BarChart>
          </ResponsiveContainer>
        </Panel>
      </div>
      <div className="lower">
        <Panel title="Derniers scans">
          <div className="scanList">
            {d.recent_scans.length ? (
              d.recent_scans.map((s: any) => (
                <div
                  key={s.id}
                  className="clickable"
                  onClick={() => (location.hash = "#/scans")}
                >
                  <Clock />
                  <span>
                    <b>{s.target}</b>
                    <small>{new Date(s.created_at).toLocaleString("fr")}</small>
                  </span>
                  <em className={"badge " + s.status}>{s.status}</em>
                </div>
              ))
            ) : (
              <Empty text="Aucun scan lancé" />
            )}
          </div>
        </Panel>
        <Panel title="Dernières alertes">
          <Empty icon={<AlertTriangle />} text="Aucune alerte récente" />
        </Panel>
      </div>
    </Layout>
  );
}
function Panel({
  title,
  children,
  className = "",
}: {
  title: string;
  children: any;
  className?: string;
}) {
  return (
    <article className={`panel ${className}`}>
      <h3>{title}</h3>
      {children}
    </article>
  );
}
function Empty({ text, icon }: { text: string; icon?: any }) {
  return (
    <div className="empty">
      {icon}
      <span>{text}</span>
    </div>
  );
}
