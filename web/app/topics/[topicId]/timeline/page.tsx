import Link from "next/link";
import { notFound } from "next/navigation";
import { PageHeader } from "@/components/PageHeader";
import { ApiError } from "@/lib/api";
import { fetchTimeline } from "@/lib/core-api";

export default async function TopicTimelinePage({
  params,
}: {
  params: Promise<{ topicId: string }>;
}) {
  const { topicId: raw } = await params;
  const topicId = Number.parseInt(raw, 10);
  if (Number.isNaN(topicId)) notFound();

  let payload: unknown;
  try {
    payload = await fetchTimeline(topicId);
  } catch (e) {
    if (e instanceof ApiError && e.status === 404) notFound();
    throw e;
  }

  const data = payload as {
    topic_id: number;
    versions: {
      version_no: number;
      title: string;
      summary?: string | null;
      generated_at: string;
    }[];
  };

  return (
    <>
      <PageHeader title="Topic timeline" />
      <p className="mb-6 text-sm text-fg-muted">
        <Link
          href={`/topics/${topicId}`}
          className="font-medium text-accent hover:underline"
        >
          ← Back to topic
        </Link>
      </p>
      <ol className="list-none space-y-6 p-0">
        {data.versions.map((v) => (
          <li
            key={v.version_no}
            className="rounded-lg border border-border bg-surface-1 p-4 shadow-sm"
          >
            <div className="flex flex-wrap items-baseline justify-between gap-2">
              <span className="font-mono text-xs text-fg-muted">
                v{v.version_no}
              </span>
              <time
                className="text-xs text-fg-muted"
                dateTime={v.generated_at}
              >
                {new Date(v.generated_at).toLocaleString()}
              </time>
            </div>
            <h2 className="mt-2 font-display text-lg font-semibold text-fg">
              {v.title}
            </h2>
            {v.summary ? (
              <p className="mt-2 text-sm leading-relaxed text-fg-muted">
                {v.summary}
              </p>
            ) : null}
          </li>
        ))}
      </ol>
    </>
  );
}
