import { useEffect, useState } from "react";
import { api } from "./api";

export type AppRole = "admin" | "operator" | "viewer";
export type CurrentUser = { id?: string; username?: string; role?: AppRole };

export const cachedUser = (): CurrentUser =>
  JSON.parse(localStorage.getItem("user") || "{}");
export const canOperate = (user: CurrentUser) =>
  user.role === "admin" || user.role === "operator";
export const isAdmin = (user: CurrentUser) => user.role === "admin";

export function useCurrentUser() {
  const [user, setUser] = useState<CurrentUser>(cachedUser);
  useEffect(() => {
    api<CurrentUser>("/auth/me")
      .then((fresh) => {
        setUser(fresh);
        localStorage.setItem("user", JSON.stringify(fresh));
      })
      .catch(() => undefined);
  }, []);
  return user;
}
