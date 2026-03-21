import { Suspense } from "react";
import { PageHeader } from "@/components/PageHeader";
import { ApiError, apiGet } from "@/lib/api";
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
  const mode =
    typeof modeRaw === "string" ? modeRaw : "keyword";
  const typeRaw = sp.type;
  const type = typeof typeRaw === "string" ? typeRaw : "all";

  let initialData: unknown = null;
  let initialError: ApiError | null = null;
  if (q?.trim()) {
    const params = new URLSearchParams({
      q: q.trim(),
      mode,
      type,
    });
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
          initialData={initialData}
          initialError={initialError}
        />
      </Suspense>
    </>
  );
}
