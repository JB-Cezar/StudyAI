import type { ChatMessage } from "../../api/types";
import "./MessageBubble.css";

export function MessageBubble({ role, content }: ChatMessage) {
  return (
    <div className={`message message--${role}`}>
      <div className="message__bubble">{content}</div>
    </div>
  );
}
