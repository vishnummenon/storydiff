import { getServerApiBase } from "./env";

export type Envelope<T> = {
  data: T | null;
  meta: Record<string, unknown>;
  error: { code: string; message: string } | null;
};

export class ApiError extends Error {
  constructor(
    public readonly status: number,
    public readonly code: string,
    message: string,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

export function unwrapEnvelope<T>(json: Envelope<T>): T {
  if (json.error) {
    throw new ApiError(400, json.error.code, json.error.message);
  }
  if (json.data === null || json.data === undefined) {
    throw new ApiError(500, "INVALID_RESPONSE", "Missing data");
  }
  return json.data;
}

export type ApiGetInit = RequestInit & {
  next?: { revalidate?: number | false; tags?: string[] };
};

/**
 * Server Components: uses API_BASE_URL (FastAPI). Pass `next: { revalidate }` for ISR.
 */
export async function apiGet<T>(path: string, init?: ApiGetInit): Promise<T> {
  const base = getServerApiBase();
  const url = `${base}${path.startsWith("/") ? path : `/${path}`}`;
  const res = await fetch(url, {
    ...init,
    headers: {
      Accept: "application/json",
      ...init?.headers,
    },
  });
  let json: Envelope<T>;
  try {
    json = (await res.json()) as Envelope<T>;
  } catch {
    throw new ApiError(res.status, "PARSE_ERROR", "Invalid JSON response");
  }
  if (process.env.API_DEBUG === "1") {
    console.log(
      `[api] ${res.status} ${url}\n`,
      JSON.stringify(json, null, 2),
    );
  }
  if (!res.ok) {
    const code = json.error?.code ?? "HTTP_ERROR";
    const msg = json.error?.message ?? res.statusText;
    throw new ApiError(res.status, code, msg);
  }
  return unwrapEnvelope(json);
}
