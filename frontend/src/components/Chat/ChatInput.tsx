import { useState } from "react";
import type { FormEvent } from "react";
import "./ChatInput.css";

interface Props {
  disabled: boolean;
  onSend: (message: string) => void;
}

export function ChatInput({ disabled, onSend }: Props) {
  const [value, setValue] = useState("");

  function handleSubmit(event: FormEvent) {
    event.preventDefault();
    const trimmed = value.trim();
    if (!trimmed || disabled) return;
    onSend(trimmed);
    setValue("");
  }

  return (
    <form className="chat-input" onSubmit={handleSubmit}>
      <input
        type="text"
        value={value}
        onChange={(e) => setValue(e.target.value)}
        placeholder="Digite sua mensagem..."
        disabled={disabled}
      />
      <button type="submit" disabled={disabled || !value.trim()}>
        Enviar
      </button>
    </form>
  );
}
