# web-application Specification

## Purpose

Normative requirements for the StoryDiff **Next.js** public web application: SSR-first pages, Core Read API integration, shared UI conventions, and operational assumptions. Backend behavior remains defined by [core-read-api](../../../../specs/core-read-api/spec.md).

## ADDED Requirements

### Requirement: Web app lives in `web/` and uses Next.js App Router

The system SHALL provide a Next.js application under repository path **`web/`** using the **App Router** (`app/` directory). The application SHALL be buildable with **`next build`** and runnable in development with **`next dev`**.

#### Scenario: Developer runs the web app locally

- **WHEN** a developer installs dependencies in **`web/`** and runs the documented dev command with the backend reachable
- **THEN** the application SHALL serve HTTP on the configured port (default **3000**) without requiring Python tooling for the Node runtime

### Requirement: All Core Read data is fetched from documented HTTP endpoints

The web application SHALL obtain read-only data exclusively by calling the Core Read API paths defined in [architecture/api_contract.md](../../../../../architecture/api_contract.md) §8 and [openspec/specs/core-read-api/spec.md](../../../../specs/core-read-api/spec.md), including **`GET /api/v1/categories`**, **`GET /api/v1/feed`**, **`GET /api/v1/topics/{topicId}`**, **`GET /api/v1/topics/{topicId}/timeline`**, **`GET /api/v1/media`**, **`GET /api/v1/media/{mediaId}`**, and **`GET /api/v1/search`**. The frontend SHALL NOT embed SQL, Qdrant, or LangGraph execution logic.

#### Scenario: Topic page uses topic endpoint

- **WHEN** a user opens a topic detail route
- **THEN** the server or client SHALL request **`GET /api/v1/topics/{topicId}`** (with supported query parameters as needed) and render from the response **`data`**

### Requirement: Responses use the common JSON envelope

The web application SHALL parse successful and error payloads using the **`{ data, meta, error }`** envelope. On HTTP **404** or API-level errors with **`error`** populated, the UI SHALL present a clear **not found** or **error** state without throwing unhandled exceptions to the user.

#### Scenario: Unknown topic shows not found

- **WHEN** **`GET /api/v1/topics/{topicId}`** returns **404** with a structured **`error`**
- **THEN** the topic route SHALL render a dedicated not-found or error view

### Requirement: Routes cover home feed, topic, timeline, media, and search

The web application SHALL implement user-facing routes for: **topic detail**; **topic timeline** (either a dedicated route or an in-page section); **media list and detail**; and **search**. The **default route `/` SHALL be the feed home**: it SHALL load **category/topic browsing** using **`GET /api/v1/categories`** and **`GET /api/v1/feed`** (same content as the product “feed” experience—not a separate marketing-only landing page). Exact pathnames for non-root routes MAY follow Next.js conventions (e.g. **`/topics/[topicId]`**, **`/media/[mediaId]`**, **`/search`**) and SHALL be documented in **`web/README.md`**.

#### Scenario: Home page is the feed

- **WHEN** a user navigates to **`/`**
- **THEN** the response SHALL render the feed/browse experience (categories and topic tiles from the feed API), not a standalone splash page that omits that content

#### Scenario: Search issues API request with mode

- **WHEN** a user submits a search with query string **`q`** and optional **`mode`** of **`keyword`**, **`semantic`**, or **`hybrid`**
- **THEN** the application SHALL call **`GET /api/v1/search`** with equivalent parameters and render **`data.results`**

### Requirement: Search uses mixed rendering

The **search** experience SHALL use **SSR or server components** for the initial document shell (layout, empty state) and **client components** for interactive controls (query input, mode selection, loading transitions) as needed. Non-interactive result lists MAY remain server-rendered when data is stable for a given navigation.

#### Scenario: User changes search mode client-side

- **WHEN** a user changes **`mode`** without a full page reload
- **THEN** the application SHALL fetch updated results and update the UI without requiring backend changes

### Requirement: Content pages are SSR-first with revalidation where appropriate

The **home feed (`/`)**, **topic detail**, and **media** pages SHALL default to **server-side rendering** for HTML. At least the **home feed** and **topic detail** routes SHALL set **`revalidate`** (or equivalent Next.js caching metadata) to a documented interval so pages are not fully static-only unless explicitly chosen.

#### Scenario: Home feed sets revalidation

- **WHEN** the **`/`** route module exports caching configuration
- **THEN** **`revalidate`** SHALL be a positive integer or the project SHALL document why it is zero/disabled

### Requirement: Configuration uses environment-based API base URL

The web application SHALL read the Core Read API origin from environment variables, minimally **`NEXT_PUBLIC_API_BASE_URL`** for browser-accessible requests. **`web/.env.example`** SHALL list required variables and example values for local development (e.g. backend at **`http://127.0.0.1:8000`**).

#### Scenario: Local development targets backend

- **WHEN** **`NEXT_PUBLIC_API_BASE_URL`** points to the local FastAPI host
- **THEN** API requests from the browser SHALL target **`/api/v1/...`** on that origin

### Requirement: UI uses shared design tokens and app shell

The web application SHALL apply **Tailwind CSS** with **CSS variables** for typography scale, neutral backgrounds and text hierarchy, a single **accent** color for links and primary actions, consistent **spacing** and **border radius**, and documented **breakpoints**. All major routes SHALL use a shared **app shell** (header/navigation, consistent max content width, optional footer) and shared patterns for **cards**, **lists**, and **tabular** data so feed, topics, media, and search feel like one product.

#### Scenario: Two routes share header and content width

- **WHEN** a user navigates from feed to a topic page
- **THEN** navigation chrome and horizontal page margins SHALL remain consistent

### Requirement: Accessibility baseline

Interactive controls SHALL be keyboard operable; focus states SHALL be visible; pages SHALL use semantic landmarks (**`header`**, **`nav`**, **`main`**, **`footer`** as appropriate). Search and async regions SHALL use appropriate **ARIA** attributes where dynamic content updates occur.

#### Scenario: Keyboard user activates search

- **WHEN** a user tabs to the search input and submits
- **THEN** the application SHALL not rely solely on pointer events to run the query

### Requirement: Explicit non-goals for v1

The web application SHALL NOT implement **authentication**, **authorization**, **write** paths, or **ingestion/admin** consoles as part of this capability. **Dark mode** SHALL NOT be required for v1.

#### Scenario: No login UI

- **WHEN** a user visits any public route
- **THEN** the application SHALL NOT present a sign-in or account flow required to read public content
