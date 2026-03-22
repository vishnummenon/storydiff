## Why

The Core Read API (`/api/v1/*`) exists, but there is no **public web application** for StoryDiff. **architecture/build_order.md** Phase 4 calls for connecting a **Next.js SSR** frontend; **architecture/hld.md** §4.6 and §13 require an SEO-friendly, read-heavy UI (**home feed** at `/`, topic detail, media, search) with SSR and sensible caching—without duplicating backend logic in the client.

## What Changes

- Add a **`web/`** Next.js **App Router** application: **SSR-first** routes where the **root path `/` is the feed (category/topic browsing via feed + categories—not a separate marketing-only landing)**, plus topic detail (+ timeline), media list/detail, and a **mixed** search experience (SSR shell + interactive query/mode/results against **`GET /api/v1/search`**).
- Implement a **shared UI system**: single app shell (nav, max content width), **editorial + data-dense** tone, consistent **loading / empty / error** patterns, and **accessibility** (landmarks, focus, keyboard-navigable controls). **Tailwind CSS + CSS variables** for tokens (typography, neutrals, one accent, spacing, radius, breakpoints); **light theme only** for v1 (dark mode explicitly out of scope).
- Add a typed **API client** layer that parses the Core Read **JSON envelope** `{ data, meta, error }` and maps HTTP errors (e.g. 404) to user-visible states—no reimplementation of ranking, SQL, or Qdrant in the frontend.
- Document **deployment guidance** in design: env-based **`NEXT_PUBLIC_API_BASE_URL`** (or server-only `API_BASE_URL` where appropriate), Next **`revalidate`** for feed/topic-style pages, and **CDN** expectations (static assets + cacheable public HTML via the hosting platform—no custom CDN code in-repo unless the repo already standardizes it).

## Capabilities

### New Capabilities

- `web-application`: Next.js SSR (and hybrid search) public frontend; routes, Core Read API consumption, envelope handling, UI conventions, caching/env/CORS assumptions, and explicit non-goals (auth, writes, admin).

### Modified Capabilities

- _(none — backend `core-read-api` requirements are unchanged; this change adds a client only.)_

## Impact

- **New:** `web/` — `package.json`, Next config, App Router routes, shared components, API helpers, Tailwind + global CSS variables.
- **Runtime:** Node.js for dev/build; browser targets modern evergreen; backend must be reachable from server (SSR) and browser (client navigations) per CORS and URL config.
- **Docs:** Satisfies **architecture/build_order.md** Phase 4 line and **hld.md** §4.6 / §13 for the web slice.

## UX intent (summary)

Ship a **cohesive** product surface: one visual language across feed, topics, media, and search—**no pixel-perfect mockups** required in this proposal; detailed tokens and patterns live in **design.md** and the **`web-application`** spec.
