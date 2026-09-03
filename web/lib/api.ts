import type { Game, TurnRequest } from "./types";
export class ApiError extends Error {
  constructor(
    message: string,
    public status: number,
  ) {
    super(message);
  }
}
async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`/api${path}`, {
    ...init,
    headers: { "Content-Type": "application/json", ...init?.headers },
    cache: "no-store",
  });
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    throw new ApiError(
      typeof body.detail === "string"
        ? body.detail
        : "La demande n’a pas pu être traitée. Réessayez.",
      response.status,
    );
  }
  return response.json();
}
export const api = {
  create: () => request<Game>("/games", { method: "POST" }),
  get: (id: string) => request<Game>(`/games/${encodeURIComponent(id)}`),
  advance: (id: string, input: TurnRequest) =>
    request<Game>(`/games/${encodeURIComponent(id)}/turns`, {
      method: "POST",
      body: JSON.stringify(input),
    }),
};
