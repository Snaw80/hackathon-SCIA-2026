import type {
  AnswersRequest,
  ConfirmationRequest,
  Game,
  TurnRequest,
} from "./types";
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
        : "The request could not be processed. Please try again.",
      response.status,
    );
  }
  return response.json();
}
export const api = {
  create: () => request<Game>("/games", { method: "POST" }),
  get: (id: string) => request<Game>(`/games/${encodeURIComponent(id)}`),
  command: (id: string, input: TurnRequest) =>
    request<Game>(`/games/${encodeURIComponent(id)}/turns`, {
      method: "POST",
      body: JSON.stringify(input),
    }),
  confirm: (id: string, runId: string, input: ConfirmationRequest) =>
    request<Game>(
      `/games/${encodeURIComponent(id)}/runs/${encodeURIComponent(runId)}/confirmation`,
      { method: "POST", body: JSON.stringify(input) },
    ),
  answer: (id: string, runId: string, input: AnswersRequest) =>
    request<Game>(
      `/games/${encodeURIComponent(id)}/runs/${encodeURIComponent(runId)}/answers`,
      { method: "POST", body: JSON.stringify(input) },
    ),
  retry: (id: string, runId: string) =>
    request<Game>(
      `/games/${encodeURIComponent(id)}/runs/${encodeURIComponent(runId)}/retry`,
      {
        method: "POST",
        body: JSON.stringify({ request_id: crypto.randomUUID() }),
      },
    ),
};
