## Context

StoryDiff’s backend exposes read endpoints under **`/api/v1`** with a common JSON envelope (see [openspec/specs/core-read-api/spec.md](../../../specs/core-read-api/spec.md) and [architecture/api_contract.md](../../../architecture/api_contract.md)). There is no `web/` app yet. This change adds a **Next.js** consumer optimized for **SSR**, **SEO**, and a consistent **editorial + data-dense** UI.

## Goals / Non-Goals

**Goals:**

- **App Router** Next.js app under **`web/`** with routes: **`/` = feed home** (categories + **`GET /api/v1/feed`** tiles—the primary entry, not a separate splash page); **`/topics/[topicId]`**, optional **`/topics/[topicId]/timeline`**, **`/media`**, **`/media/[mediaId]`**, **`/search`**. Optional alias **`/feed` → `/`** is allowed for bookmarks but not required.
- **Server Components** by default for document-style pages; **Client Components** only where interactivity is required (search: query input, mode `keyword | semantic | hybrid`, results updates).
- **API integration** via small fetch helpers (or a minimal client module) calling **`NEXT_PUBLIC_API_BASE_URL`** / server **`API_BASE_URL`**—single place to unwrap `{ data, meta, error }` and throw or return typed errors for 404/5xx.
- **Caching:** `export const revalidate = N` on suitable routes (feed, topic detail); tune `N` per freshness needs (document in code comments).
- **Styling:** **Tailwind CSS v4** (or latest stable in lockstep with Next) + **CSS custom properties** in `:root` for tokens; shared primitives: `AppShell`, `PageHeader`, `TopicCard`, `DataTable`/`LeaderboardRow`, `EmptyState`, `ErrorState`, `LoadingSkeleton`.
- **Accessibility:** semantic `<header>/<nav>/<main>/<footer>`, visible focus, `aria-*` on search/live regions as needed, sufficient contrast on neutrals + accent.

**Non-Goals:**

- Authentication, sessions, or write APIs; ingestion/admin UIs.
- **Dark mode** in v1 (explicitly deferred).
- Custom **CDN** or **CloudFront** code in this repo; document that **static `_next/static` and `public/`** are served via the platform CDN when deployed (Vercel/Cloudflare/AWS + CloudFront, etc.).
- E2E test grid across all browsers (smoke + a11y lint optional follow-up).

## Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Framework | Next.js App Router | Matches HLD §13; SSR + `revalidate` + future edge if needed. |
| CSS | Tailwind + CSS variables | Fast iteration, design tokens without a heavy component library; variables enable one accent + neutrals. |
| API base URL | `NEXT_PUBLIC_API_BASE_URL` for browser; mirror or server-only `API_BASE_URL` for RSC/server fetch if secrets ever needed | Simple local dev (`http://127.0.0.1:8000`) vs production; document in `web/.env.example`. |
| Envelope parsing | Single `apiFetch` / `unwrapEnvelope` helper | Avoid duplicating envelope logic per route; centralize error mapping. |
| Search UX | URL search params (`?q=&mode=`) optional | Shareable URLs; SSR can read `searchParams` for first paint. |
| Topic timeline | Nested section on topic page **or** `/topics/[id]/timeline` | Either is fine; pick one in implementation for consistent nav (tasks cover both options—implement one). |
| Root route | **`/` renders the feed UI** | Single home surface; matches “read-heavy” product and avoids duplicate landing vs browse. |

**Alternatives considered:** CSS Modules only (rejected: slower for dense dashboards); full UI kit (MUI/Chakra) (rejected: heavier than needed for v1).

## Risks / Trade-offs

| Risk | Mitigation |
|------|------------|
| CORS blocks browser calls to API | Configure FastAPI CORS for dev origins; prod: same-site proxy or allowed origins documented in backend. |
| SSR calls wrong API URL in prod | Validate env at build/start; document required vars. |
| Semantic search needs Qdrant up | Surface API error message in search UI; keyword mode still works if backend allows. |
| Design drift across pages | Land tokens + shell early (tasks order). |

## Migration Plan

1. Add `web/` with lockfile; `npm install` / `pnpm install` per team choice.
2. Local dev: run backend on `:8000`, Next on `:3000`, set `NEXT_PUBLIC_API_BASE_URL`.
3. Production: build `next build`; run `next start` or platform build output; set env vars; no DB migrations (frontend only).

**Rollback:** Remove or stop deploying `web/`; backend unchanged.

## Open Questions

- **Package manager:** npm vs pnpm vs yarn—align with repo preference when adding `web/` (if none, default **pnpm** or **npm** and record in `web/README.md`).
- **Exact `revalidate` seconds** per route—start with conservative values (e.g. 60–300s) and adjust after observing data freshness.

## CDN / edge (guidance)

- **Static:** Next emits hashed assets under `_next/static/`; `public/` files are static. Hosting on Vercel/Cloudflare/AWS places these behind a CDN automatically.
- **SSR HTML:** Cacheable only when `Cache-Control` / platform defaults / `revalidate` allow; do not bake proprietary CDN logic into app code unless the monorepo already has shared infra modules.
