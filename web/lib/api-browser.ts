import { ApiError, unwrapEnvelope, type Envelope } from "./api";

/** Same-origin `/api/v1/...` (rewrites to FastAPI). For client components only. */
export async function browserApiGet<T>(pathAndQuery: string): Promise<T> {
  const path = pathAndQuery.startsWith("/") ? pathAndQuery : `/${pathAndQuery}`;
  const res = await fetch(path);
  let json: Envelope<T>;
  try {
    json = (await res.json()) as Envelope<T>;
  } catch {
    throw new ApiError(res.status, "PARSE_ERROR", "Invalid JSON response");
  }
  if (!res.ok) {
    const code = json.error?.code ?? "HTTP_ERROR";
    const msg = json.error?.message ?? res.statusText;
    throw new ApiError(res.status, code, msg);
  }
  return unwrapEnvelope(json);
}
