export interface VinylListItem {
  id: string;
  title: string;
  artist: string;
  image_url: string | null;
  year: number | null;
  genres: string[];
  min_price: number | null;
  currency: string;
  in_stock: boolean;
  source_count: number;
  slug: string | null;
  youtube_url: string | null;
}

export interface VinylSourceOut {
  source_name: string;
  external_url: string;
  price: number;
  currency: string;
  in_stock: boolean;
  scraped_at: string;
}

export interface TrackOut {
  position: string;
  title: string;
  duration: string | null;
  youtube_url: string | null;
}

export interface VinylDetail {
  id: string;
  title: string;
  artist: string;
  label: string | null;
  catalog_number: string | null;
  year: number | null;
  condition: string | null;
  image_url: string | null;
  og_image_url: string | null;
  slug: string | null;
  musicbrainz_id: string | null;
  youtube_url: string | null;
  created_at: string;
  updated_at: string;
  genres: string[];
  sources: VinylSourceOut[];
  tracklist: TrackOut[];
}

export interface PaginatedResponse {
  items: VinylListItem[];
  total: number;
  page: number;
  per_page: number;
  pages: number;
}

export interface GenreOut {
  id: string;
  name: string;
  slug: string;
  vinyl_count: number;
}

export interface SourceOut {
  id: string;
  name: string;
  base_url: string;
  enabled: boolean;
  last_scraped_at: string | null;
}

export interface StatsOut {
  total_vinyls: number;
  in_stock: number;
  sources: number;
  top_genres: Record<string, number>;
  last_updated_at: string | null;
}

export interface SearchParams {
  q?: string;
  genre?: string | string[];
  source?: string | string[];
  in_stock?: boolean;
  price_min?: number;
  price_max?: number;
  condition?: string;
  sort?: string;
  page?: number;
  per_page?: number;
}
