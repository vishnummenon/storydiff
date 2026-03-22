import Link from "next/link";
import type { TopicTile } from "@/lib/core-api";

export function TopicCard({ topic }: { topic: TopicTile }) {
  return (
    <Link
      href={`/topics/${topic.id}`}
      className="group block rounded-lg border border-border bg-surface-1 p-4 shadow-sm transition-shadow hover:border-accent/40 hover:shadow-md focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent"
    >
      <h3 className="font-display text-base font-semibold leading-snug text-fg group-hover:text-accent">
        {topic.title}
      </h3>
      {topic.summary ? (
        <p className="mt-2 line-clamp-3 text-sm text-fg-muted">{topic.summary}</p>
      ) : null}
      <dl className="mt-3 flex flex-wrap gap-x-4 gap-y-1 text-xs text-fg-muted">
        <div>
          <dt className="inline sr-only">Articles</dt>
          <dd className="inline">{topic.article_count} articles</dd>
        </div>
        <div>
          <dt className="inline sr-only">Sources</dt>
          <dd className="inline">{topic.source_count} sources</dd>
        </div>
        {topic.reliability_score != null ? (
          <div>
            <dt className="inline sr-only">Reliability</dt>
            <dd className="inline">
              {(topic.reliability_score * 100).toFixed(0)}% reliability
            </dd>
          </div>
        ) : null}
      </dl>
    </Link>
  );
}
