import { useState } from "react";
import type { FormEvent } from "react";
import * as calendarApi from "../../api/calendar";

interface Props {
  onCreated: () => void;
}

export function ManualEventForm({ onCreated }: Props) {
  const [title, setTitle] = useState("");
  const [date, setDate] = useState("");
  const [startTime, setStartTime] = useState("");
  const [endTime, setEndTime] = useState("");
  const [description, setDescription] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    if (!title.trim() || !date || !startTime || !endTime) {
      setError("Preencha título, data, início e fim.");
      return;
    }

    setBusy(true);
    setError(null);
    try {
      await calendarApi.createEvent({
        title: title.trim(),
        start: `${date}T${startTime}:00-03:00`,
        end: `${date}T${endTime}:00-03:00`,
        description: description.trim() || null,
      });
      setTitle("");
      setDate("");
      setStartTime("");
      setEndTime("");
      setDescription("");
      onCreated();
    } catch {
      setError("Não foi possível criar o evento.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <details className="calendar-panel__manual-form">
      <summary>Criar evento manualmente</summary>
      <form onSubmit={handleSubmit}>
        {error && <p className="calendar-panel__error">{error}</p>}
        <input
          type="text"
          placeholder="Título"
          value={title}
          onChange={(e) => setTitle(e.target.value)}
        />
        <div className="calendar-panel__manual-form-row">
          <input type="date" value={date} onChange={(e) => setDate(e.target.value)} />
          <input type="time" value={startTime} onChange={(e) => setStartTime(e.target.value)} />
          <input type="time" value={endTime} onChange={(e) => setEndTime(e.target.value)} />
        </div>
        <textarea
          placeholder="Descrição (opcional)"
          value={description}
          onChange={(e) => setDescription(e.target.value)}
        />
        <button type="submit" disabled={busy}>
          {busy ? "Criando..." : "Criar no calendário"}
        </button>
      </form>
    </details>
  );
}
