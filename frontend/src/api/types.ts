export interface ChatMessage {
  role: "user" | "assistant";
  content: string;
}

export interface CalendarAction {
  title: string;
  start: string;
  end: string;
  description?: string | null;
}

export interface ChatResponse {
  reply: string;
  actions: CalendarAction[];
}

export interface CalendarStatus {
  configured: boolean;
  authenticated: boolean;
  write_access: boolean;
}

export interface CalendarEvent {
  raw: Record<string, unknown>;
  label: string;
}

export interface User {
  id: number;
  email: string;
  name: string;
  picture?: string | null;
}
