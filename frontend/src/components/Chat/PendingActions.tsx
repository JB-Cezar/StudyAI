import type { CalendarAction } from "../../api/types";
import "./PendingActions.css";

function formatLabel(action: CalendarAction): string {
  const start = action.start.slice(0, 16).replace("T", " ");
  const end = action.end.slice(0, 16).replace("T", " ");
  return `${action.title} (${start} → ${end})`;
}

interface Props {
  actions: CalendarAction[];
  onConfirm: (action: CalendarAction, index: number) => void;
  pendingIndex: number | null;
}

export function PendingActions({ actions, onConfirm, pendingIndex }: Props) {
  if (actions.length === 0) return null;

  return (
    <div className="pending-actions">
      <h3>📅 Sugestões para o calendário</h3>
      <p className="pending-actions__hint">
        Confirme antes de criar — nada é salvo sem seu clique.
      </p>
      {actions.map((action, index) => (
        <button
          key={`${action.title}-${action.start}`}
          type="button"
          className="pending-actions__button"
          disabled={pendingIndex !== null}
          onClick={() => onConfirm(action, index)}
        >
          {pendingIndex === index ? "Criando..." : `Criar: ${formatLabel(action)}`}
        </button>
      ))}
    </div>
  );
}
