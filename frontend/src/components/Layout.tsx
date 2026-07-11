import {
  Activity,
  Archive,
  Box,
  Building2,
  ChartNoAxesCombined,
  ChevronLeft,
  FlaskConical,
  FileText,
  Globe2,
  LogOut,
  Menu,
  Network,
  ScanSearch,
  Server,
  Settings,
} from "lucide-react";
import { ReactNode, useState } from "react";
const nav = [
  ["Tableau de bord", ChartNoAxesCombined, "#/"],
  ["Scans", ScanSearch, "#/scans"],
];
export function Layout({
  children,
  title,
}: {
  children: ReactNode;
  title: string;
}) {
  const [open, setOpen] = useState(true),
    user = JSON.parse(localStorage.getItem("user") || "{}"),
    current = "#" + (location.hash.slice(1).split("?")[0] || "/");
  const Link = ({
    href,
    icon: Icon,
    label,
  }: {
    href: string;
    icon: any;
    label: string;
  }) => (
    <a className={current === href ? "active" : ""} href={href}>
      <Icon />
      <span>{label}</span>
    </a>
  );
  return (
    <div className={"shell " + (!open ? "collapsed" : "")}>
      <aside>
        <div className="brand">
          <div className="mark">
            <Activity />
          </div>
          <b>NetScope</b>
          <button className="icon" onClick={() => setOpen(!open)}>
            {open ? <ChevronLeft /> : <Menu />}
          </button>
        </div>
        <small>VUE PRINCIPALE</small>
        <nav>
          {nav.map(([label, Icon, href]: any) => (
            <Link key={href} href={href} icon={Icon} label={label} />
          ))}
        </nav>
        <small>INFRASTRUCTURE LAB</small>
        <nav>
          <Link href="#/lab" icon={FlaskConical} label="Vue d’ensemble" />
          <Link href="#/datacenter" icon={Building2} label="Datacenter" />
          <Link href="#/assets" icon={Server} label="Équipements" />
          <Link href="#/ipam" icon={Globe2} label="IPAM" />
          <Link href="#/networks" icon={Globe2} label="Réseaux" />
          <Link href="#/topology" icon={Network} label="Relations" />
        </nav>
        <small>INTELLIGENCE</small>
        <nav>
          <Link href="#/vendors" icon={Box} label="Constructeurs" />
        </nav>
        <small>ADMINISTRATION</small>
        <nav>
          <Link href="#/reports" icon={FileText} label="Rapports" />
          <Link href="#/archives" icon={Archive} label="Archives" />
          <Link href="#/settings" icon={Settings} label="Paramètres" />
        </nav>
        <div className="asideFoot">
          <span>NetScope v0.1.0</span>
        </div>
      </aside>
      <main>
        <header>
          <h2>{title}</h2>
          <div className="user">
            <div className="avatar">
              {(user.username || "A")[0].toUpperCase()}
            </div>
            <span>
              <b>{user.username || "admin"}</b>
              <small>{user.role || "administrateur"}</small>
            </span>
            <button
              className="icon"
              title="Déconnexion"
              onClick={() => {
                localStorage.clear();
                location.hash = "#/login";
              }}
            >
              <LogOut />
            </button>
          </div>
        </header>
        <section className="content">{children}</section>
      </main>
    </div>
  );
}
