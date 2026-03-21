/**
 * Server-side fetch should hit FastAPI directly (faster, no double hop).
 * Client-side fetch uses same-origin `/api/v1/...` (rewritten to FastAPI in next.config).
 */
export function getServerApiBase(): string {
  const raw =
    process.env.API_BASE_URL?.trim() ||
    process.env.NEXT_PUBLIC_API_BASE_URL?.trim() ||
    "http://127.0.0.1:8000";
  return raw.replace(/\/$/, "");
}

/** Browser / client components: empty string = same origin (rewrites). */
export function getClientApiPrefix(): string {
  return "";
}
