import { useCallback, useEffect, useState } from "react";
import { loginUrl } from "../api/auth";
import * as calendarApi from "../api/calendar";
import * as chatApi from "../api/chat";
import { ApiError } from "../api/client";
import type { CalendarAction, CalendarStatus, ChatMessage, User } from "../api/types";
import { ChatInput } from "../components/Chat/ChatInput";
import { ChatWindow } from "../components/Chat/ChatWindow";
import { PendingActions } from "../components/Chat/PendingActions";
import { Sidebar } from "../components/Sidebar/Sidebar";
import "./ChatPage.css";

export function ChatPage() {
  // undefined = ainda não sabemos (checando /auth/me); null = confirmado deslogado.
  const [user, setUser] = useState<User | null | undefined>(undefined);

  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [pendingActions, setPendingActions] = useState<CalendarAction[]>([]);
  const [isThinking, setIsThinking] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [calendarStatus, setCalendarStatus] = useState<CalendarStatus | null>(null);
  const [usarCalendario, setUsarCalendario] = useState(false);
  const [permitirCriar, setPermitirCriar] = useState(false);
  const [creatingIndex, setCreatingIndex] = useState<number | null>(null);
  const [feedback, setFeedback] = useState<string | null>(null);

  useEffect(() => {
    if (!user) return;
    chatApi.getHistory().then(setMessages).catch(() => setMessages([]));
  }, [user]);

  const handleAuthChange = useCallback((nextUser: User | null) => {
    setUser(nextUser);
    if (!nextUser) {
      setMessages([]);
      setPendingActions([]);
    }
  }, []);

  const handleNewConversation = useCallback(() => {
    chatApi.resetHistory().finally(() => {
      setMessages([]);
      setPendingActions([]);
      setError(null);
    });
  }, []);

  async function handleSend(text: string) {
    setError(null);
    setMessages((prev) => [...prev, { role: "user", content: text }]);
    setIsThinking(true);
    try {
      const { reply, actions } = await chatApi.sendMessage(text, usarCalendario, permitirCriar);
      setMessages((prev) => [...prev, { role: "assistant", content: reply }]);
      setPendingActions(actions);
    } catch (e) {
      setMessages((prev) => prev.slice(0, -1));
      const detail = e instanceof ApiError ? e.message : null;
      setError(`❌ ${detail || "Erro ao gerar resposta."}`);
    } finally {
      setIsThinking(false);
    }
  }

  async function handleConfirmAction(action: CalendarAction, index: number) {
    setCreatingIndex(index);
    setFeedback(null);
    try {
      await calendarApi.createEvent(action);
      setPendingActions((prev) => prev.filter((_, i) => i !== index));
      setFeedback(`Evento criado: ${action.title}`);
    } catch {
      setFeedback("Não foi possível criar o evento.");
    } finally {
      setCreatingIndex(null);
    }
  }

  return (
    <div className="chat-page">
      <Sidebar
        user={user}
        messageCount={messages.length}
        onNewConversation={handleNewConversation}
        onAuthChange={handleAuthChange}
        calendarStatus={calendarStatus}
        onCalendarStatusChange={setCalendarStatus}
        usarCalendario={usarCalendario}
        onToggleUsarCalendario={setUsarCalendario}
        permitirCriar={permitirCriar}
        onTogglePermitirCriar={setPermitirCriar}
      />

      <main className="chat-page__main">
        <header className="chat-page__header">
          <h1>🧠 StudyAI</h1>
          <p>Assistente Inteligente para Organização de Estudos</p>
        </header>

        {feedback && <div className="chat-page__feedback">{feedback}</div>}
        {error && <div className="chat-page__error">{error}</div>}

        {user === undefined ? null : user === null ? (
          <div className="chat-page__login-gate">
            <p>Entre com sua conta Google para conversar com o StudyAI.</p>
            <a className="chat-page__login-button" href={loginUrl()}>
              🔑 Entrar com Google
            </a>
          </div>
        ) : (
          <>
            <ChatWindow messages={messages} isThinking={isThinking} />
            <PendingActions
              actions={pendingActions}
              onConfirm={handleConfirmAction}
              pendingIndex={creatingIndex}
            />
            <ChatInput disabled={isThinking} onSend={handleSend} />
          </>
        )}
      </main>
    </div>
  );
}
