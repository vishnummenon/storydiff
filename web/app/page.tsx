import { PageHeader } from "@/components/PageHeader";
import { TopicCard } from "@/components/TopicCard";
import { fetchFeed } from "@/lib/core-api";

export default async function HomePage() {
  const data = await fetchFeed(
    { limit_per_category: 12, include_empty_categories: false },
  );

  return (
    <>
      <PageHeader
        title="Feed"
        description="Topics grouped by category — your entry point into coverage and consensus."
      />
      <div className="space-y-12">
        {data.categories.length === 0 ? (
          <p className="text-sm text-fg-muted">No categories returned yet.</p>
        ) : (
          data.categories.map((cat) => (
            <section key={cat.id} aria-labelledby={`cat-${cat.id}`}>
              <h2
                id={`cat-${cat.id}`}
                className="font-display text-xl font-semibold text-fg"
              >
                {cat.name}
              </h2>
              <p className="mt-1 text-sm text-fg-muted">{cat.slug}</p>
              {cat.topics.length === 0 ? (
                <p className="mt-4 text-sm text-fg-muted">No topics in this category.</p>
              ) : (
                <ul className="mt-4 grid list-none gap-4 p-0 sm:grid-cols-2 lg:grid-cols-3">
                  {cat.topics.map((t) => (
                    <li key={t.id}>
                      <TopicCard topic={t} />
                    </li>
                  ))}
                </ul>
              )}
            </section>
          ))
        )}
      </div>
    </>
  );
}
