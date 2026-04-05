"use client";

import { useCallback, useState, useTransition } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { ApiError } from "@/lib/api";
import { browserApiGet } from "@/lib/api-browser";
import { EmptyState } from "@/components/EmptyState";
import { ErrorState } from "@/components/ErrorState";

type SearchMode = "keyword" | "semantic" | "hybrid";
type ResultType = "all" | "topics" | "articles";

type SearchPayload = {
  query: string;
  mode: string;
  results: {
    topics: {
      topic_id: number;
      title: string;
      summary?: string | null;
      score?: number;
    }[];
    articles: {
      article_id: number;
      title: string;
      url: string;
      score?: number;
      media_outlet?: { name: string };
    }[];
  };
};

export function SearchPanel({
  initialQ,
  initialMode,
  initialType,
  initialCategory,
  initialFrom,
  initialTo,
  initialData,
  initialError,
  categories,
}: {
  initialQ: string;
  initialMode: string;
  initialType: string;
  initialCategory: string;
  initialFrom: string;
  initialTo: string;
  initialData: unknown;
  initialError: ApiError | null;
  categories: { slug: string; name: string }[];
}) {
  const router = useRouter();
  const [q, setQ] = useState(initialQ);
  const [mode, setMode] = useState<SearchMode>(
    (initialMode as SearchMode) || "keyword",
  );
  const [type, setType] = useState<ResultType>(
    (initialType as ResultType) || "all",
  );
  const [category, setCategory] = useState(initialCategory);
  const [fromDate, setFromDate] = useState(initialFrom);
  const [toDate, setToDate] = useState(initialTo);
  const [error, setError] = useState<ApiError | null>(initialError);
  const [results, setResults] = useState<SearchPayload | null>(
    initialData && !initialError ? (initialData as SearchPayload) : null,
  );
  const [isPending, startTransition] = useTransition();

  const run = useCallback(
    (query: string, m: SearchMode, t: ResultType, cat: string, from: string, to: string) => {
      const trimmed = query.trim();
      if (!trimmed) {
        setResults(null);
        setError(null);
        router.replace("/search", { scroll: false });
        return;
      }
      startTransition(async () => {
        setError(null);
        const params = new URLSearchParams({ q: trimmed, mode: m, type: t });
        if (cat) params.set("category", cat);
        if (from) params.set("from", from);
        if (to) params.set("to", to);
        try {
          const data = await browserApiGet<SearchPayload>(
            `/api/v1/search?${params.toString()}`,
          );
          setResults(data);
          router.replace(`/search?${params.toString()}`, { scroll: false });
        } catch (e) {
          if (e instanceof ApiError) {
            setError(e);
            setResults(null);
          } else throw e;
        }
      });
    },
    [router],
  );

  const onSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    run(q, mode, type, category, fromDate, toDate);
  };

  return (
    <div>
      <form
        onSubmit={onSubmit}
        className="rounded-lg border border-border bg-surface-1 p-4 shadow-sm"
        role="search"
        aria-label="Site search"
      >
        <div className="flex flex-col gap-4 md:flex-row md:items-end">
          <div className="min-w-0 flex-1">
            <label htmlFor="search-q" className="text-xs font-medium text-fg-muted">
              Query
            </label>
            <input
              id="search-q"
              name="q"
              type="search"
              value={q}
              onChange={(e) => setQ(e.target.value)}
              className="mt-1 w-full rounded-md border border-border bg-surface-0 px-3 py-2 text-fg shadow-sm focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent"
              placeholder="Keywords…"
              autoComplete="off"
            />
          </div>
          <div>
            <label htmlFor="search-mode" className="text-xs font-medium text-fg-muted">
              Mode
            </label>
            <select
              id="search-mode"
              name="mode"
              value={mode}
              onChange={(e) => setMode(e.target.value as SearchMode)}
              className="mt-1 w-full rounded-md border border-border bg-surface-0 px-3 py-2 text-sm text-fg focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent md:w-40"
            >
              <option value="keyword">Keyword</option>
              <option value="semantic">Semantic</option>
              <option value="hybrid">Hybrid</option>
            </select>
          </div>
          <div>
            <label htmlFor="search-type" className="text-xs font-medium text-fg-muted">
              Result type
            </label>
            <select
              id="search-type"
              name="type"
              value={type}
              onChange={(e) => setType(e.target.value as ResultType)}
              className="mt-1 w-full rounded-md border border-border bg-surface-0 px-3 py-2 text-sm text-fg focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent md:w-36"
            >
              <option value="all">All</option>
              <option value="topics">Topics</option>
              <option value="articles">Articles</option>
            </select>
          </div>
          {categories.length > 0 && (
            <div>
              <label htmlFor="search-category" className="text-xs font-medium text-fg-muted">
                Category
              </label>
              <select
                id="search-category"
                name="category"
                value={category}
                onChange={(e) => setCategory(e.target.value)}
                className="mt-1 w-full rounded-md border border-border bg-surface-0 px-3 py-2 text-sm text-fg focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent md:w-40"
              >
                <option value="">All categories</option>
                {categories.map((c) => (
                  <option key={c.slug} value={c.slug}>
                    {c.name}
                  </option>
                ))}
              </select>
            </div>
          )}
          <div>
            <label htmlFor="search-from" className="text-xs font-medium text-fg-muted">
              From
            </label>
            <input
              id="search-from"
              name="from"
              type="date"
              value={fromDate}
              onChange={(e) => setFromDate(e.target.value)}
              className="mt-1 w-full rounded-md border border-border bg-surface-0 px-3 py-2 text-sm text-fg shadow-sm focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent md:w-36"
            />
          </div>
          <div>
            <label htmlFor="search-to" className="text-xs font-medium text-fg-muted">
              To
            </label>
            <input
              id="search-to"
              name="to"
              type="date"
              value={toDate}
              onChange={(e) => setToDate(e.target.value)}
              className="mt-1 w-full rounded-md border border-border bg-surface-0 px-3 py-2 text-sm text-fg shadow-sm focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent md:w-36"
            />
          </div>
          <button
            type="submit"
            disabled={isPending}
            className="rounded-md bg-accent px-4 py-2 text-sm font-medium text-white shadow-sm hover:bg-accent-muted focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent disabled:opacity-60"
          >
            {isPending ? "Searching…" : "Search"}
          </button>
        </div>
      </form>

      <div className="mt-8" aria-live="polite">
        {!q.trim() && !results && !error ? (
          <EmptyState
            title="Search StoryDiff"
            detail="Enter a query. Keyword mode works without vector search; semantic and hybrid need the backend embedding stack and Qdrant when enabled."
          />
        ) : null}

        {error ? (
          <ErrorState
            title={error.status === 503 ? "Search unavailable" : "Search failed"}
            code={error.code}
            message={error.message}
          />
        ) : null}

        {results ? (
          <div className="space-y-8">
            <p className="text-sm text-fg-muted">
              Mode: <span className="font-mono">{results.mode}</span> · Query:{" "}
              <span className="font-mono">{results.query}</span>
            </p>
            {(type === "all" || type === "topics") &&
            results.results.topics.length > 0 ? (
              <section aria-labelledby="topics-h">
                <h2 id="topics-h" className="font-display text-lg font-semibold">
                  Topics
                </h2>
                <ul className="mt-3 divide-y divide-border rounded-lg border border-border bg-surface-1">
                  {results.results.topics.map((t) => (
                    <li key={t.topic_id} className="p-4">
                      <Link
                        href={`/topics/${t.topic_id}`}
                        className="font-medium text-accent hover:underline"
                      >
                        {t.title}
                      </Link>
                      {t.summary ? (
                        <p className="mt-1 line-clamp-2 text-sm text-fg-muted">
                          {t.summary}
                        </p>
                      ) : null}
                      {typeof t.score === "number" ? (
                        <p className="mt-1 text-xs text-fg-muted">
                          score {t.score.toFixed(4)}
                        </p>
                      ) : null}
                    </li>
                  ))}
                </ul>
              </section>
            ) : null}
            {(type === "all" || type === "articles") &&
            results.results.articles.length > 0 ? (
              <section aria-labelledby="articles-h">
                <h2 id="articles-h" className="font-display text-lg font-semibold">
                  Articles
                </h2>
                <ul className="mt-3 divide-y divide-border rounded-lg border border-border bg-surface-1">
                  {results.results.articles.map((a) => (
                    <li key={a.article_id} className="p-4">
                      <a
                        href={a.url}
                        target="_blank"
                        rel="noreferrer"
                        className="font-medium text-accent hover:underline"
                      >
                        {a.title}
                      </a>
                      {a.media_outlet ? (
                        <p className="mt-1 text-xs text-fg-muted">
                          {a.media_outlet.name}
                        </p>
                      ) : null}
                    </li>
                  ))}
                </ul>
              </section>
            ) : null}
            {results.results.topics.length === 0 &&
            results.results.articles.length === 0 ? (
              <EmptyState title="No results" detail="Try different keywords or mode." />
            ) : null}
          </div>
        ) : null}
      </div>
    </div>
  );
}
