import Link from "next/link";
import { notFound } from "next/navigation";
import { PageHeader } from "@/components/PageHeader";
import { ApiError } from "@/lib/api";
import { fetchMediaDetail } from "@/lib/core-api";

export default async function MediaDetailPage({
  params,
}: {
  params: Promise<{ mediaId: string }>;
}) {
  const { mediaId: raw } = await params;
  const mediaId = Number.parseInt(raw, 10);
  if (Number.isNaN(mediaId)) notFound();

  let rawData: unknown;
  try {
    rawData = await fetchMediaDetail(mediaId, { window: "30d" });
  } catch (e) {
    if (e instanceof ApiError && e.status === 404) notFound();
    throw e;
  }

  const data = rawData as {
    media_outlet: { id: number; name: string; slug: string };
    overall_metrics: Record<string, unknown>;
    by_category: { category: string }[];
    recent_topics: {
      topic_id: number;
      title: string;
      article_count: number;
      last_seen_at?: string | null;
    }[];
  };

  return (
    <>
      <PageHeader
        title={data.media_outlet.name}
        description={`Slug: ${data.media_outlet.slug}`}
      />
      <section className="mb-8 rounded-lg border border-border bg-surface-1 p-4">
        <h2 className="font-display text-base font-semibold">Window metrics</h2>
        <pre className="mt-2 max-h-48 overflow-auto rounded bg-surface-2 p-3 font-mono text-xs text-fg-muted">
          {JSON.stringify(data.overall_metrics, null, 2)}
        </pre>
      </section>
      {data.by_category.length > 0 ? (
        <section className="mb-8">
          <h2 className="font-display text-lg font-semibold">By category</h2>
          <ul className="mt-2 list-disc pl-5 text-sm text-fg-muted">
            {data.by_category.map((c) => (
              <li key={c.category}>{c.category}</li>
            ))}
          </ul>
        </section>
      ) : null}
      <section>
        <h2 className="font-display text-lg font-semibold">Recent topics</h2>
        {data.recent_topics.length === 0 ? (
          <p className="mt-2 text-sm text-fg-muted">None in this window.</p>
        ) : (
          <ul className="mt-3 space-y-2">
            {data.recent_topics.map((t) => (
              <li key={t.topic_id}>
                <Link
                  href={`/topics/${t.topic_id}`}
                  className="font-medium text-accent hover:underline"
                >
                  {t.title}
                </Link>
                <span className="ml-2 text-xs text-fg-muted">
                  {t.article_count} articles
                </span>
              </li>
            ))}
          </ul>
        )}
      </section>
    </>
  );
}
