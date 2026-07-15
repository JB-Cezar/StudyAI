import { api } from "./client";
import type { CalendarAction, CalendarEvent, CalendarStatus } from "./types";

export function getStatus(): Promise<CalendarStatus> {
  return api.get<CalendarStatus>("/calendar/status");
}

export function disconnect(): Promise<CalendarStatus> {
  return api.post<CalendarStatus>("/calendar/disconnect");
}

export function listEvents(): Promise<CalendarEvent[]> {
  return api.get<CalendarEvent[]>("/calendar/events");
}

export function createEvent(action: CalendarAction): Promise<unknown> {
  return api.post("/calendar/events", action);
}
