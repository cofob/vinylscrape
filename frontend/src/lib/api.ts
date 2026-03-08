import type {
  GenreOut,
  PaginatedResponse,
  SearchParams,
  SourceOut,
  StatsOut,
  VinylDetail,
} from "@/types/vinyl";

const API_BASE = "/api/v1";

async function fetchJSON<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...init?.headers,
    },
  });
  if (!res.ok) {
    throw new Error(`API error: ${res.status} ${res.statusText}`);
  }
  return res.json() as Promise<T>;
}

export async function searchVinyls(
  params: SearchParams
): Promise<PaginatedResponse> {
  const query = new URLSearchParams();
  if (params.q) query.set("q", params.q);
  if (params.genre && params.genre.length > 0)
    query.set("genre", Array.isArray(params.genre) ? params.genre.join(",") : params.genre);
  if (params.source && params.source.length > 0)
    query.set("source", Array.isArray(params.source) ? params.source.join(",") : params.source);
  if (params.in_stock !== undefined)
    query.set("in_stock", String(params.in_stock));
  if (params.price_min !== undefined)
    query.set("price_min", String(params.price_min));
  if (params.price_max !== undefined)
    query.set("price_max", String(params.price_max));
  if (params.condition) query.set("condition", params.condition);
  if (params.sort) query.set("sort", params.sort);
  if (params.page) query.set("page", String(params.page));
  if (params.per_page) query.set("per_page", String(params.per_page));

  return fetchJSON<PaginatedResponse>(`/vinyl?${query.toString()}`);
}

export async function getVinyl(id: string): Promise<VinylDetail> {
  return fetchJSON<VinylDetail>(`/vinyl/${id}`);
}

export async function getGenres(params?: {
  q?: string;
  source?: string | string[];
  in_stock?: boolean;
  genre?: string[];
  condition?: string;
}): Promise<GenreOut[]> {
  const query = new URLSearchParams();
  if (params?.q) query.set("q", params.q);
  if (params?.source && params.source.length > 0)
    query.set("source", Array.isArray(params.source) ? params.source.join(",") : params.source);
  if (params?.in_stock !== undefined)
    query.set("in_stock", String(params.in_stock));
  if (params?.genre && params.genre.length > 0)
    query.set("genre", params.genre.join(","));
  if (params?.condition) query.set("condition", params.condition);
  const qs = query.toString();
  return fetchJSON<GenreOut[]>(`/genres${qs ? `?${qs}` : ""}`);
}

export async function getSources(): Promise<SourceOut[]> {
  return fetchJSON<SourceOut[]>("/sources");
}

export async function getStats(): Promise<StatsOut> {
  return fetchJSON<StatsOut>("/stats");
}
