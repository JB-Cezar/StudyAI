import { API_BASE_URL, api } from "./client";
import type { User } from "./types";

export function loginUrl(): string {
  return `${API_BASE_URL}/auth/google/login`;
}

export function getMe(): Promise<User> {
  return api.get<User>("/auth/me");
}

export function logout(): Promise<void> {
  return api.post<void>("/auth/logout");
}
