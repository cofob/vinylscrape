import { getVinylSitemapServer } from "@/lib/api-server";

const CACHE_TTL_MS = 24 * 60 * 60 * 1000; // 1 day

let cachedXml: string | null = null;
let cacheExpiresAt = 0;

const STATIC_PAGES = [
  { url: "https://vinylscrape.cfb.wtf", changefreq: "daily", priority: "1.0" },
  { url: "https://vinylscrape.cfb.wtf/about", changefreq: "monthly", priority: "0.5" },
  { url: "https://vinylscrape.cfb.wtf/docs/api", changefreq: "monthly", priority: "0.3" },
];

function escapeXml(s: string): string {
  return s
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&apos;");
}

async function buildSitemapXml(): Promise<string> {
  const vinyls = await getVinylSitemapServer();

  const staticEntries = STATIC_PAGES.map(
    (p) =>
      `  <url>\n    <loc>${escapeXml(p.url)}</loc>\n    <changefreq>${p.changefreq}</changefreq>\n    <priority>${p.priority}</priority>\n  </url>`,
  ).join("\n");

  const vinylEntries = vinyls
    .map((v) => {
      const loc = escapeXml(`https://vinylscrape.cfb.wtf/vinyl/${v.slug ?? v.id}`);
      const lastmod = new Date(v.updated_at).toISOString().split("T")[0];
      return `  <url>\n    <loc>${loc}</loc>\n    <lastmod>${lastmod}</lastmod>\n    <changefreq>weekly</changefreq>\n    <priority>0.8</priority>\n  </url>`;
    })
    .join("\n");

  return `<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n${staticEntries}\n${vinylEntries}\n</urlset>`;
}

export async function GET(): Promise<Response> {
  const now = Date.now();

  if (!cachedXml || now >= cacheExpiresAt) {
    cachedXml = await buildSitemapXml();
    cacheExpiresAt = now + CACHE_TTL_MS;
  }

  const secondsRemaining = Math.floor((cacheExpiresAt - Date.now()) / 1000);

  return new Response(cachedXml, {
    headers: {
      "Content-Type": "application/xml; charset=utf-8",
      "Cache-Control": `public, max-age=${secondsRemaining}, s-maxage=${secondsRemaining}, stale-while-revalidate=3600`,
    },
  });
}
