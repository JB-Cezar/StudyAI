import { useEffect, useState } from "react";
import * as authApi from "../../api/auth";
import { ApiError } from "../../api/client";
import type { User } from "../../api/types";
import "./AuthPanel.css";

interface Props {
  onAuthChange: (user: User | null) => void;
}

export function AuthPanel({ onAuthChange }: Props) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    authApi
      .getMe()
      .then((u) => {
        setUser(u);
        onAuthChange(u);
      })
      .catch((e) => {
        if (!(e instanceof ApiError) || e.status !== 401) {
          console.error(e);
        }
        setUser(null);
        onAuthChange(null);
      })
      .finally(() => setLoading(false));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function handleLogout() {
    await authApi.logout();
    setUser(null);
    onAuthChange(null);
  }

  if (loading) return null;

  if (!user) {
    return (
      <a className="auth-panel__login" href={authApi.loginUrl()}>
        🔑 Entrar com Google
      </a>
    );
  }

  return (
    <div className="auth-panel__user">
      {user.picture && <img className="auth-panel__avatar" src={user.picture} alt="" />}
      <div className="auth-panel__info">
        <span className="auth-panel__name">{user.name}</span>
        <button type="button" className="auth-panel__logout" onClick={handleLogout}>
          Sair
        </button>
      </div>
    </div>
  );
}
