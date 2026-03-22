import { apiGet, type ApiGetInit } from "./api";

export type CategoryRow = {
  id: number;
  slug: string;
  name: string;
  display_order?: number;
};

export type TopicTile = {
  id: number;
  title: string;
  summary?: string | null;
  article_count: number;
  source_count: number;
  reliability_score?: number | null;
  last_updated_at?: string | null;
};

export type FeedCategoryBlock = {
  id: number;
  slug: string;
  name: string;
  topics: TopicTile[];
};

export type FeedData = { categories: FeedCategoryBlock[] };

export type CategoriesData = { categories: CategoryRow[] };

export async function fetchCategories(init?: ApiGetInit): Promise<CategoriesData> {
  return apiGet<CategoriesData>("/api/v1/categories", init);
}

export async function fetchFeed(
  params: {
    category?: string;
    limit_per_category?: number;
    include_empty_categories?: boolean;
  } = {},
  init?: ApiGetInit,
): Promise<FeedData> {
  const sp = new URLSearchParams();
  if (params.category) sp.set("category", params.category);
  if (params.limit_per_category != null)
    sp.set("limit_per_category", String(params.limit_per_category));
  if (params.include_empty_categories != null)
    sp.set("include_empty_categories", String(params.include_empty_categories));
  const q = sp.toString();
  return apiGet<FeedData>(`/api/v1/feed${q ? `?${q}` : ""}`, init);
}

export async function fetchTopic(
  topicId: number,
  params: { include_articles?: boolean; include_timeline_preview?: boolean } = {},
  init?: ApiGetInit,
) {
  const sp = new URLSearchParams();
  if (params.include_articles != null)
    sp.set("include_articles", String(params.include_articles));
  if (params.include_timeline_preview != null)
    sp.set("include_timeline_preview", String(params.include_timeline_preview));
  const q = sp.toString();
  return apiGet<unknown>(
    `/api/v1/topics/${topicId}${q ? `?${q}` : ""}`,
    init,
  );
}

export async function fetchTimeline(topicId: number, init?: ApiGetInit) {
  return apiGet<unknown>(`/api/v1/topics/${topicId}/timeline`, init);
}

export async function fetchMediaLeaderboard(
  params: {
    category?: string;
    window?: string;
    limit?: number;
    sort_by?: string;
  } = {},
  init?: ApiGetInit,
) {
  const sp = new URLSearchParams();
  if (params.category) sp.set("category", params.category);
  if (params.window) sp.set("window", params.window);
  if (params.limit != null) sp.set("limit", String(params.limit));
  if (params.sort_by) sp.set("sort_by", params.sort_by);
  const q = sp.toString();
  return apiGet<unknown>(`/api/v1/media${q ? `?${q}` : ""}`, init);
}

export async function fetchMediaDetail(
  mediaId: number,
  params: { window?: string } = {},
  init?: ApiGetInit,
) {
  const sp = new URLSearchParams();
  if (params.window) sp.set("window", params.window);
  const q = sp.toString();
  return apiGet<unknown>(
    `/api/v1/media/${mediaId}${q ? `?${q}` : ""}`,
    init,
  );
}
