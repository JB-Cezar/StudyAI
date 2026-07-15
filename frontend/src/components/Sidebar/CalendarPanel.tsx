import { useEffect, useState } from "react";
import { loginUrl } from "../../api/auth";
import * as calendarApi from "../../api/calendar";
import type { CalendarEvent, CalendarStatus, User } from "../../api/types";
import { ManualEventForm } from "./ManualEventForm";
import "./CalendarPanel.css";

interface Props {
  user: User | null | undefined;
  onStatusChange: (status: CalendarStatus) => void;
}

export function CalendarPanel({ user, onStatusChange }: Props) {
  const [status, setStatus] = useState<CalendarStatus | null>(null);
  const [events, setEvents] = useState<CalendarEvent[]>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function refreshStatus() {
    const s = await calendarApi.getStatus();
    setStatus(s);
    onStatusChange(s);
    return s;
  }

  async function refreshEvents() {
    try {
      setEvents(await calendarApi.listEvents());
    } catch {
      setEvents([]);
    }
  }

  useEffect(() => {
    if (!user) {
      setStatus(null);
      setEvents([]);
      return;
    }
    refreshStatus()
      .then((s) => {
        if (s.authenticated) refreshEvents();
      })
      .catch(() => setError("Não foi possível checar o status do calendário."));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [user]);

  async function handleDisconnect() {
    setBusy(true);
    try {
      await calendarApi.disconnect();
      await refreshStatus();
      setEvents([]);
    } finally {
      setBusy(false);
    }
  }

  if (!user) {
    return <p className="calendar-panel__hint">Entre com Google para conectar o calendário.</p>;
  }

  if (!status) {
    return <p className="calendar-panel__hint">Carregando status do calendário...</p>;
  }

  if (!status.configured) {
    return (
      <p className="calendar-panel__hint">
        <code>GOOGLE_CLIENT_ID</code>/<code>GOOGLE_CLIENT_SECRET</code> não configurados no
        backend. Veja SETUP_CALENDAR.md.
      </p>
    );
  }

  return (
    <div className="calendar-panel">
      {error && <p className="calendar-panel__error">{error}</p>}

      {status.authenticated ? (
        <>
          <p className="calendar-panel__status calendar-panel__status--ok">
            Calendário conectado
          </p>
          <p className="calendar-panel__hint">
            {status.write_access ? "Permissão de leitura e escrita ativa." : "Somente leitura."}
          </p>
          <div className="calendar-panel__actions">
            <button type="button" disabled={busy} onClick={refreshEvents}>
              🔄 Atualizar eventos
            </button>
            <button type="button" disabled={busy} onClick={handleDisconnect}>
              Desconectar
            </button>
          </div>

          {events.length > 0 && (
            <details className="calendar-panel__events" open>
              <summary>Próximos compromissos</summary>
              <ul>
                {events.map((event) => (
                  <li key={event.label}>{event.label}</li>
                ))}
              </ul>
            </details>
          )}

          {status.write_access && <ManualEventForm onCreated={refreshEvents} />}
        </>
      ) : (
        <>
          <p className="calendar-panel__hint">
            O login não incluiu acesso ao Calendar (ou você desconectou). Entre com Google de
            novo para reconectar.
          </p>
          <a className="auth-panel__login" href={loginUrl()}>
            🔗 Conectar Google Calendar
          </a>
        </>
      )}
    </div>
  );
}
