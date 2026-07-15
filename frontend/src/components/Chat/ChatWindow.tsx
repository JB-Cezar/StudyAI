import { useEffect, useRef } from "react";
import type { ChatMessage } from "../../api/types";
import { MessageBubble } from "./MessageBubble";
import "./ChatWindow.css";

interface Props {
  messages: ChatMessage[];
  isThinking: boolean;
}

export function ChatWindow({ messages, isThinking }: Props) {
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isThinking]);

  if (messages.length === 0 && !isThinking) {
    return (
      <div className="chat-window chat-window--empty">
        <p>
          Peça ajuda para organizar a semana, priorizar provas ou agendar blocos de estudo.
        </p>
      </div>
    );
  }

  return (
    <div className="chat-window">
      {messages.map((message, index) => (
        <MessageBubble key={index} role={message.role} content={message.content} />
      ))}
      {isThinking && (
        <div className="message message--assistant">
          <div className="message__bubble message__bubble--thinking">
            StudyAI está pensando...
          </div>
        </div>
      )}
      <div ref={bottomRef} />
    </div>
  );
}
