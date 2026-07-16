import React, { lazy, Suspense } from "react";
import { createRoot } from "react-dom/client";
import "./style.css";
import "./interactions.css";
import "./management.css";
import "./ui.css";
import { token } from "./lib/api";
const Datacenter = lazy(() =>
    import("./pages/Datacenter").then((x) => ({ default: x.Datacenter })),
  ),
  Alerts = lazy(() =>
    import("./pages/Alerts").then((x) => ({ default: x.Alerts })),
  ),
  Reports = lazy(() =>
    import("./pages/Reports").then((x) => ({ default: x.Reports })),
  ),
  Lab = lazy(() => import("./pages/Lab").then((x) => ({ default: x.Lab }))),
  Archives = lazy(() =>
    import("./pages/Archives").then((x) => ({ default: x.Archives })),
  ),
  Login = lazy(() =>
    import("./pages/Login").then((x) => ({ default: x.Login })),
  ),
  Dashboard = lazy(() =>
    import("./pages/Dashboard").then((x) => ({ default: x.Dashboard })),
  ),
  Assets = lazy(() =>
    import("./pages/Assets").then((x) => ({ default: x.Assets })),
  ),
  AssetDetail = lazy(() =>
    import("./pages/AssetDetail").then((x) => ({ default: x.AssetDetail })),
  ),
  Scans = lazy(() =>
    import("./pages/Scans").then((x) => ({ default: x.Scans })),
  ),
  Connectors = lazy(() =>
    import("./pages/Connectors").then((x) => ({ default: x.Connectors })),
  ),
  Networks = lazy(() =>
    import("./pages/Networks").then((x) => ({ default: x.Networks })),
  ),
  Topology = lazy(() =>
    import("./pages/Topology").then((x) => ({ default: x.Topology })),
  ),
  Ipam = lazy(() => import("./pages/Ipam").then((x) => ({ default: x.Ipam }))),
  Settings = lazy(() =>
    import("./pages/Settings").then((x) => ({ default: x.Settings })),
  ),
  Vendors = lazy(() =>
    import("./pages/Vendors").then((x) => ({ default: x.Vendors })),
  ),
  Users = lazy(() =>
    import("./pages/Users").then((x) => ({ default: x.Users })),
  ),
  Layout = lazy(() =>
    import("./components/Layout").then((x) => ({ default: x.Layout })),
  );
function App() {
  if (!token()) return <Login />;
  const path = (location.hash.slice(1) || "/").split("?")[0];
  if (path === "/") return <Dashboard />;
  if (path === "/alerts") return <Alerts />;
  if (path === "/lab") return <Lab />;
  if (path === "/datacenter") return <Datacenter />;
  if (path === "/assets") return <Assets />;
  if (path.startsWith("/assets/"))
    return <AssetDetail id={path.split("/")[2]} />;
  if (path === "/ipam") return <Ipam />;
  if (path === "/settings") return <Settings />;
  if (path === "/users") return <Users />;
  if (path === "/reports") return <Reports />;
  if (path === "/archives") return <Archives />;
  if (path === "/vendors") return <Vendors />;
  if (path === "/scans") return <Scans />;
  if (path === "/connectors") return <Connectors />;
  if (path === "/networks") return <Networks />;
  if (path === "/topology") return <Topology />;
  return (
    <Layout title="Page introuvable">
      <article className="panel future">
        <h2>Page introuvable</h2>
        <a href="#/">Retour au tableau de bord</a>
      </article>
    </Layout>
  );
}
const root = createRoot(document.getElementById("root")!),
  render = () =>
    root.render(
      <React.StrictMode>
        <Suspense fallback={<div className="loading">Chargement…</div>}>
          <App />
        </Suspense>
      </React.StrictMode>,
    );
window.addEventListener("hashchange", render);
render();
