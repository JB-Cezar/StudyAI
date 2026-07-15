import type { CalendarStatus, User } from "../../api/types";
import { AuthPanel } from "./AuthPanel";
import { CalendarPanel } from "./CalendarPanel";
import "./Sidebar.css";

interface Props {
  user: User | null | undefined;
  messageCount: number;
  onNewConversation: () => void;
  onAuthChange: (user: User | null) => void;
  calendarStatus: CalendarStatus | null;
  onCalendarStatusChange: (status: CalendarStatus) => void;
  usarCalendario: boolean;
  onToggleUsarCalendario: (value: boolean) => void;
  permitirCriar: boolean;
  onTogglePermitirCriar: (value: boolean) => void;
}

export function Sidebar({
  user,
  messageCount,
  onNewConversation,
  onAuthChange,
  calendarStatus,
  onCalendarStatusChange,
  usarCalendario,
  onToggleUsarCalendario,
  permitirCriar,
  onTogglePermitirCriar,
}: Props) {
  return (
    <aside className="sidebar">
      <section className="sidebar__section">
        <AuthPanel onAuthChange={onAuthChange} />
      </section>

      <hr />

      <section className="sidebar__section">
        <h2>💬 Conversa</h2>
        <button type="button" className="sidebar__new-chat" onClick={onNewConversation}>
          Nova conversa
        </button>
        <p className="sidebar__caption">
          {messageCount} mensagem(ns) nesta sessão. O agente lembra o que você disse até
          clicar em Nova conversa.
        </p>
      </section>

      <hr />

      <section className="sidebar__section">
        <h2>📅 Google Calendar</h2>
        <CalendarPanel user={user} onStatusChange={onCalendarStatusChange} />

        {calendarStatus?.authenticated && (
          <div className="sidebar__toggles">
            <label className="calendar-panel__checkbox">
              <input
                type="checkbox"
                checked={usarCalendario}
                onChange={(e) => onToggleUsarCalendario(e.target.checked)}
              />
              Usar calendário nas respostas
            </label>
            <label className="calendar-panel__checkbox">
              <input
                type="checkbox"
                checked={permitirCriar}
                disabled={!calendarStatus.write_access}
                onChange={(e) => onTogglePermitirCriar(e.target.checked)}
              />
              IA pode sugerir eventos para criar
            </label>
          </div>
        )}
      </section>
    </aside>
  );
}
