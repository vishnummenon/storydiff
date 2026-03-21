# StoryDiff web

Next.js (App Router) frontend for the Core Read API. The home page **`/`** is the **feed** (categories + topic tiles).

## Commands

```bash
npm install
cp .env.example .env.local   # optional; defaults match local FastAPI
npm run dev                  # http://localhost:3000
npm run build && npm start   # production
npm run lint
```

## API & env

- **Server-side** requests use **`API_BASE_URL`** (see `.env.example`) to call FastAPI directly, e.g. `http://127.0.0.1:8000/api/v1/...`.
- **Browser** requests use same-origin **`/api/v1/...`**. `next.config.ts` **rewrites** those to the backend (`BACKEND_URL` / `API_BASE_URL` / default `127.0.0.1:8000`), so you typically **do not need CORS** for local dev.
- If you point the browser at **`NEXT_PUBLIC_API_BASE_URL`** to another origin instead of using rewrites, you must enable CORS on FastAPI for the Next origin (see `backend/src/storydiff/main.py` — add `CORSMiddleware` if you go that route).

## Caching & deploy

- The root layout sets **`dynamic = 'force-dynamic'`** so `next build` succeeds **without** a live API. Per-request SSR is the default; to use **ISR** (`revalidate`) and static prerendering later, relax that (e.g. remove `force-dynamic` from `app/layout.tsx`) and ensure the API is reachable at build time, or use incremental adoption per route.
- **CDN:** static assets (`_next/static/`, `public/`) and HTML are served by your host’s CDN (Vercel, Cloudflare, etc.); no extra CDN code in this package.

## Stack

- Next.js 15, React 19, TypeScript, Tailwind CSS, CSS variables for tokens (see `app/globals.css`).
