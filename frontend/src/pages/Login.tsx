import { FormEvent, useState } from "react";
import { Activity, LockKeyhole } from "lucide-react";
import { login } from "../lib/api";
export function Login() {
  const [error, setError] = useState("");
  async function submit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const f = new FormData(e.currentTarget);
    try {
      await login(
        String(f.get("username")),
        String(f.get("password")),
        String(f.get("mfa") || ""),
      );
      location.hash = "#/";
    } catch (x: any) {
      setError(
        x.message === "MFA_REQUIRED"
          ? "Saisissez le code de votre application MFA"
          : x.message,
      );
    }
  }
  return (
    <div className="login">
      <form onSubmit={submit}>
        <div className="loginBrand">
          <Activity />
          <h1>NetScope</h1>
        </div>
        <p>Inventaire et découverte réseau</p>
        <label>
          Nom d’utilisateur
          <input name="username" defaultValue="admin" autoFocus />
        </label>
        <label>
          Mot de passe
          <input name="password" type="password" />
        </label>
        <label>
          Code MFA (si activé)
          <input
            name="mfa"
            inputMode="numeric"
            maxLength={6}
            placeholder="123456"
          />
        </label>
        {error && <div className="error">{error}</div>}
        <button className="primary">
          <LockKeyhole />
          Se connecter
        </button>
      </form>
    </div>
  );
}
