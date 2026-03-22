import Link from "next/link";
import { notFound } from "next/navigation";
import { PageHeader } from "@/components/PageHeader";
import { ApiError } from "@/lib/api";
import { fetchTopic } from "@/lib/core-api";

type TopicBlock = {
  id: number;
  title: string;
  summary: string | null;
  category?: { name: string; slug: string };
  article_count: number;
  source_count: number;
  reliability_score?: number | null;
};

type ArticleScores = {
  consensus_distance: number | null;
  framing_polarity: number | null;
  source_diversity_score: number | null;
  novel_claim_score: number | null;
  reliability_score: number | null;
};

type ArticleRow = {
  article_id: number;
  title: string;
  url: string;
  published_at?: string | null;
  media_outlet?: { name: string; slug: string };
  summary?: string | null;
  scores?: ArticleScores | null;
  polarity_labels?: string[];
};

export default async function TopicPage({
  params,
}: {
  params: Promise<{ topicId: string }>;
}) {
  const { topicId: raw } = await params;
  const topicId = Number.parseInt(raw, 10);
  if (Number.isNaN(topicId)) notFound();

  let payload: unknown;
  try {
    payload = await fetchTopic(topicId, {
      include_articles: true,
      include_timeline_preview: true,
    });
  } catch (e) {
    if (e instanceof ApiError && e.status === 404) notFound();
    throw e;
  }

  const data = payload as {
    topic: TopicBlock;
    articles?: ArticleRow[];
    timeline_preview?: { version_no: number; title: string; generated_at: string }[];
  };
  const { topic, articles = [], timeline_preview = [] } = data;

  return (
    <>
      <PageHeader
        title={topic.title}
        description={topic.summary ?? undefined}
      />
      <div className="mb-6 flex flex-wrap gap-3 text-sm">
        {topic.category ? (
          <span className="rounded-md bg-surface-2 px-2 py-1 text-fg-muted">
            {topic.category.name}
          </span>
        ) : null}
        <span className="text-fg-muted">
          {topic.article_count} articles · {topic.source_count} sources
        </span>
        {topic.reliability_score != null ? (
          <span className="text-fg-muted">
            Reliability {(topic.reliability_score * 100).toFixed(0)}%
          </span>
        ) : null}
        <Link
          href={`/topics/${topicId}/timeline`}
          className="font-medium text-accent hover:underline focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent"
        >
          Full timeline
        </Link>
      </div>

      {timeline_preview.length > 0 ? (
        <section className="mb-10" aria-labelledby="preview-label">
          <h2 id="preview-label" className="font-display text-lg font-semibold">
            Recent versions
          </h2>
          <ol className="mt-3 list-decimal space-y-2 pl-5 text-sm text-fg-muted">
            {timeline_preview.map((v) => (
              <li key={v.version_no}>
                <span className="text-fg">{v.title}</span>
                <span className="ml-2 text-xs">
                  v{v.version_no} · {new Date(v.generated_at).toLocaleString()}
                </span>
              </li>
            ))}
          </ol>
        </section>
      ) : null}

      <section aria-labelledby="articles-label">
        <h2 id="articles-label" className="font-display text-lg font-semibold">
          Articles
        </h2>
        {articles.length === 0 ? (
          <p className="mt-3 text-sm text-fg-muted">No articles linked.</p>
        ) : (
          <ul className="mt-4 divide-y divide-border rounded-lg border border-border bg-surface-1">
            {articles.map((a) => (
              <li key={a.article_id} className="p-4">
                <a
                  href={a.url}
                  target="_blank"
                  rel="noreferrer"
                  className="font-medium text-accent hover:underline focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent"
                >
                  {a.title}
                </a>
                {a.media_outlet ? (
                  <p className="mt-1 text-xs text-fg-muted">{a.media_outlet.name}</p>
                ) : null}
                {a.summary ? (
                  <p className="mt-2 text-sm text-fg-muted line-clamp-3">{a.summary}</p>
                ) : null}
                {a.scores ? (
                  <dl className="mt-3 flex flex-wrap gap-x-5 gap-y-1 text-xs">
                    {a.scores.consensus_distance != null ? (
                      <div className="flex items-center gap-1">
                        <dt className="text-fg-muted">Variance</dt>
                        <dd className="font-medium tabular-nums">
                          {(a.scores.consensus_distance * 100).toFixed(0)}%
                        </dd>
                      </div>
                    ) : null}
                    {a.scores.framing_polarity != null ? (
                      <div className="flex items-center gap-1">
                        <dt className="text-fg-muted">Framing</dt>
                        <dd
                          className={`font-medium tabular-nums ${
                            a.scores.framing_polarity > 0.2
                              ? "text-red-500"
                              : a.scores.framing_polarity < -0.2
                                ? "text-blue-500"
                                : "text-fg-muted"
                          }`}
                        >
                          {a.scores.framing_polarity > 0
                            ? `+${a.scores.framing_polarity.toFixed(2)}`
                            : a.scores.framing_polarity.toFixed(2)}
                        </dd>
                      </div>
                    ) : null}
                    {a.scores.reliability_score != null ? (
                      <div className="flex items-center gap-1">
                        <dt className="text-fg-muted">Reliability</dt>
                        <dd className="font-medium tabular-nums">
                          {(a.scores.reliability_score * 100).toFixed(0)}%
                        </dd>
                      </div>
                    ) : null}
                    {a.scores.novel_claim_score != null ? (
                      <div className="flex items-center gap-1">
                        <dt className="text-fg-muted">Novel claims</dt>
                        <dd className="font-medium tabular-nums">
                          {(a.scores.novel_claim_score * 100).toFixed(0)}%
                        </dd>
                      </div>
                    ) : null}
                    {a.scores.source_diversity_score != null ? (
                      <div className="flex items-center gap-1">
                        <dt className="text-fg-muted">Source diversity</dt>
                        <dd className="font-medium tabular-nums">
                          {(a.scores.source_diversity_score * 100).toFixed(0)}%
                        </dd>
                      </div>
                    ) : null}
                  </dl>
                ) : null}
                {a.polarity_labels && a.polarity_labels.length > 0 ? (
                  <ul className="mt-2 flex flex-wrap gap-1">
                    {a.polarity_labels.map((label) => (
                      <li
                        key={label}
                        className="rounded-full bg-surface-2 px-2 py-0.5 text-xs text-fg-muted"
                      >
                        {label}
                      </li>
                    ))}
                  </ul>
                ) : null}
              </li>
            ))}
          </ul>
        )}
      </section>
    </>
  );
}
