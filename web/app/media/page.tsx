import Link from "next/link";
import { PageHeader } from "@/components/PageHeader";
import { fetchMediaLeaderboard } from "@/lib/core-api";

type Outlet = { id: number; slug: string; name: string };

type LeaderItem = {
  media_outlet: Outlet;
  article_count?: number;
  composite_rank_score?: number;
  avg_consensus_distance?: number;
  avg_reliability_score?: number;
};

export default async function MediaLeaderboardPage() {
  const raw = await fetchMediaLeaderboard({
    window: "30d",
    limit: 50,
    sort_by: "composite_rank_score",
  });
  const data = raw as {
    window: string;
    category?: string | null;
    items: LeaderItem[];
  };

  return (
    <>
      <PageHeader
        title="Media leaderboard"
        description={`Outlets ranked for window ${data.window}.`}
      />
      <div className="overflow-x-auto rounded-lg border border-border">
        <table className="w-full min-w-[640px] border-collapse text-left text-sm">
          <thead>
            <tr className="border-b border-border bg-surface-2">
              <th className="p-3 font-semibold text-fg">Outlet</th>
              <th className="p-3 font-semibold text-fg">Articles</th>
              <th className="p-3 font-semibold text-fg">Rank</th>
              <th className="p-3 font-semibold text-fg">Avg reliability</th>
            </tr>
          </thead>
          <tbody>
            {data.items.length === 0 ? (
              <tr>
                <td colSpan={4} className="p-6 text-center text-fg-muted">
                  No outlets in this window.
                </td>
              </tr>
            ) : (
              data.items.map((row) => (
                <tr key={row.media_outlet.id} className="border-b border-border bg-surface-1">
                  <td className="p-3">
                    <Link
                      href={`/media/${row.media_outlet.id}`}
                      className="font-medium text-accent hover:underline focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent"
                    >
                      {row.media_outlet.name}
                    </Link>
                    <p className="text-xs text-fg-muted">{row.media_outlet.slug}</p>
                  </td>
                  <td className="p-3 tabular-nums text-fg-muted">
                    {row.article_count ?? "—"}
                  </td>
                  <td className="p-3 tabular-nums text-fg-muted">
                    {row.composite_rank_score != null
                      ? row.composite_rank_score.toFixed(3)
                      : "—"}
                  </td>
                  <td className="p-3 tabular-nums text-fg-muted">
                    {row.avg_reliability_score != null
                      ? (row.avg_reliability_score * 100).toFixed(0) + "%"
                      : "—"}
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </>
  );
}
