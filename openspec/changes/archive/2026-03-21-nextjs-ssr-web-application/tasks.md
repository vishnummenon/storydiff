## 1. Scaffold and tooling

- [x] 1.1 Create `web/` with Next.js (App Router), TypeScript, Tailwind, ESLint; add `web/README.md` with dev/prod commands
- [x] 1.2 Add `web/.env.example` with `NEXT_PUBLIC_API_BASE_URL` (and optional server-only `API_BASE_URL` if used)
- [x] 1.3 Add root or `web/` `.gitignore` entries for Next.js if not already covered by repo patterns

## 2. Design tokens and app shell

- [x] 2.1 Define global CSS variables (typography, neutrals, accent, radius, spacing) and wire Tailwind theme to them
- [x] 2.2 Implement `AppShell` (header/nav, main max-width, optional footer) and shared layout applied to all routes
- [x] 2.3 Add primitives: `PageHeader`, `EmptyState`, `ErrorState`, loading skeleton; ensure focus-visible styles

## 3. API client layer

- [x] 3.1 Implement `unwrapEnvelope` / `apiFetch` targeting `${base}/api/v1/...` with typed errors for 404/5xx
- [x] 3.2 Add thin typed functions per resource: categories, feed, topic, timeline, media list/detail, search

## 4. SSR routes and caching

- [x] 4.1 Home feed at `/`: categories + feed tiles using `GET /api/v1/categories` and `GET /api/v1/feed` (this **is** the landing experience—no separate marketing-only home); nav links to media and search; root layout uses `force-dynamic` so builds work without API (see `web/README.md` for ISR/`revalidate` later)
- [x] 4.2 Topic detail `/topics/[topicId]` using `GET /api/v1/topics/{id}`; handle 404
- [x] 4.3 Timeline: either `/topics/[topicId]/timeline` or in-page section using `GET /api/v1/topics/{id}/timeline`
- [x] 4.4 Media list `/media` and detail `/media/[mediaId]` with leaderboard and detail endpoints
- [x] 4.5 Document caching strategy: `force-dynamic` default + CDN/revalidate notes in `web/README.md`

## 5. Search (mixed client/server)

- [x] 5.1 `/search` route with SSR shell; client controls for `q`, `mode` (`keyword` \| `semantic` \| `hybrid`), submit, loading
- [x] 5.2 Map API errors (including Qdrant unavailable) to user-visible messages; empty state when no `q`

## 6. Polish and docs

- [x] 6.1 Unify list/card/table styling across feed, topics, media, search results
- [x] 6.2 Document CORS expectations for local dev (pointer to backend config) in `web/README.md`
- [x] 6.3 Note CDN/deployment: static assets and `revalidate` behavior; no in-app CDN code
