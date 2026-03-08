/**
 * Server-side API helpers that use BACKEND_URL for absolute URLs.
 * These functions must only be called from Server Components or Route Handlers.
 * They bypass the Next.js rewrites proxy and hit the backend directly.
 */

import type { VinylDetail } from "@/types/vinyl";

const BACKEND_URL = process.env.BACKEND_URL || "http://localhost:8000";
const API_BASE = `${BACKEND_URL}/api/v1`;

export interface VinylSitemapEntry {
  id: string;
  slug: string | null;
  updated_at: string;
}

const UUID_REGEX = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

export async function getVinylServer(id: string): Promise<VinylDetail | null> {
  // Determine whether `id` is a UUID or a slug and choose the right endpoint
  const url = UUID_REGEX.test(id)
    ? `${API_BASE}/vinyl/${id}`
    : `${API_BASE}/vinyl/by-slug/${encodeURIComponent(id)}`;

  try {
    const res = await fetch(url, {
      next: { revalidate: 3600 }, // revalidate every hour
    });
    if (res.status === 404) return null;
    if (!res.ok) throw new Error(`API error: ${res.status}`);
    return res.json() as Promise<VinylDetail>;
  } catch {
    return null;
  }
}

export async function getVinylSitemapServer(): Promise<VinylSitemapEntry[]> {
  try {
    const res = await fetch(`${API_BASE}/vinyl/sitemap`, {
      next: { revalidate: 3600 },
    });
    if (!res.ok) return [];
    return res.json() as Promise<VinylSitemapEntry[]>;
  } catch {
    return [];
  }
}
