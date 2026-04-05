import { Suspense } from "react";
import { PageHeader } from "@/components/PageHeader";
import { ApiError, apiGet } from "@/lib/api";
import type { CategoriesData } from "@/lib/core-api";
import { SearchPanel } from "./SearchPanel";

export default async function SearchPage({
  searchParams,
}: {
  searchParams: Promise<Record<string, string | string[] | undefined>>;
}) {
  const sp = await searchParams;

  const qRaw = sp.q;
  const q = typeof qRaw === "string" ? qRaw : undefined;
  const modeRaw = sp.mode;
  const mode = typeof modeRaw === "string" ? modeRaw : "keyword";
  const typeRaw = sp.type;
  const type = typeof typeRaw === "string" ? typeRaw : "all";
  const categoryRaw = sp.category;
  const category = typeof categoryRaw === "string" ? categoryRaw : "";
  const fromRaw = sp.from;
  const from = typeof fromRaw === "string" ? fromRaw : "";
  const toRaw = sp.to;
  const to = typeof toRaw === "string" ? toRaw : "";

  // Fetch categories server-side for the filter dropdown
  let categories: { slug: string; name: string }[] = [];
  try {
    const catData = await apiGet<CategoriesData>("/api/v1/categories", {
      cache: "no-store",
    });
    categories = catData.categories.map((c) => ({ slug: c.slug, name: c.name }));
  } catch {
    // Non-fatal — search still works without the category filter
  }

  let initialData: unknown = null;
  let initialError: ApiError | null = null;
  if (q?.trim()) {
    const params = new URLSearchParams({ q: q.trim(), mode, type });
    if (category) params.set("category", category);
    if (from) params.set("from", from);
    if (to) params.set("to", to);
    try {
      initialData = await apiGet(`/api/v1/search?${params.toString()}`, {
        cache: "no-store",
      });
    } catch (e) {
      if (e instanceof ApiError) initialError = e;
      else throw e;
    }
  }

  return (
    <>
      <PageHeader
        title="Search"
        description="Keyword search works without Qdrant; semantic and hybrid require embeddings and Qdrant on the API."
      />
      <Suspense
        fallback={
          <p className="text-sm text-fg-muted" role="status">
            Loading search…
          </p>
        }
      >
        <SearchPanel
          initialQ={q ?? ""}
          initialMode={mode}
          initialType={type}
          initialCategory={category}
          initialFrom={from}
          initialTo={to}
          initialData={initialData}
          initialError={initialError}
          categories={categories}
        />
      </Suspense>
    </>
  );
}
