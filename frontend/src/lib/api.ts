const base = "/api/v1";
export const token = () => localStorage.getItem("token");
function errorDetail(payload: unknown, fallback: string): string {
  const detail = (payload as any)?.detail ?? payload;
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail))
    return detail
      .map((item) => item?.msg || item?.message || JSON.stringify(item))
      .join(" · ");
  if (detail && typeof detail === "object")
    return detail.message || JSON.stringify(detail);
  return fallback;
}
export async function api<T>(path: string, init: RequestInit = {}): Promise<T> {
  const r = await fetch(base + path, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(token() ? { Authorization: `Bearer ${token()}` } : {}),
      ...init.headers,
    },
  });
  if (r.status === 401) {
    localStorage.removeItem("token");
    localStorage.removeItem("user");
    location.hash = "#/login";
  }
  if (!r.ok) {
    const payload = await r.json().catch(() => undefined);
    throw new Error(
      errorDetail(payload, r.statusText || `Erreur HTTP ${r.status}`),
    );
  }
  return r.json();
}
export async function login(username: string, password: string, mfa?: string) {
  const body = new URLSearchParams({ username, password });
  const r = await fetch(base + "/auth/login", {
    method: "POST",
    headers: {
      "Content-Type": "application/x-www-form-urlencoded",
      ...(mfa ? { "X-MFA-Code": mfa } : {}),
    },
    body,
  });
  if (!r.ok) {
    const payload = await r.json().catch(() => undefined);
    throw new Error(errorDetail(payload, "Identifiants invalides"));
  }
  const data = await r.json();
  localStorage.setItem("token", data.access_token);
  localStorage.setItem("user", JSON.stringify(data.user));
}
export async function downloadAssets() {
  const r = await fetch(base + "/assets/export.csv", {
    headers: { Authorization: `Bearer ${token()}` },
  });
  if (!r.ok) throw new Error("Export impossible");
  const url = URL.createObjectURL(await r.blob());
  const link = document.createElement("a");
  link.href = url;
  link.download = "netscope-assets.csv";
  link.click();
  URL.revokeObjectURL(url);
}
export type Asset = {
  id: string;
  status: string;
  hostname?: string;
  manufacturer?: string;
  model?: string;
  device_type: string;
  operating_system?: string;
  confidence: number;
  first_seen: string;
  last_seen: string;
  addresses: { address: string; version: number }[];
  identifiers: { kind: string; value: string; confidence: number }[];
  services: {
    protocol: string;
    port: number;
    name?: string;
    product?: string;
    version?: string;
  }[];
};
