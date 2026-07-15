import { api } from "./client";
import type { ChatMessage, ChatResponse } from "./types";

export function sendMessage(
  message: string,
  usarCalendario: boolean,
  permitirCriar: boolean,
): Promise<ChatResponse> {
  return api.post<ChatResponse>("/chat", {
    message,
    usar_calendario: usarCalendario,
    permitir_criar: permitirCriar,
  });
}

export function getHistory(): Promise<ChatMessage[]> {
  return api.get<ChatMessage[]>("/chat/history");
}

export function resetHistory(): Promise<void> {
  return api.post<void>("/chat/reset");
}
