import type { Metadata } from "next";
import Link from "next/link";

export const metadata: Metadata = {
  title: "API Reference",
  description:
    "REST API documentation for the VinylScrape vinyl record aggregator.",
};

/* ─── tiny helpers ─────────────────────────────────────────── */

function Badge({
  method,
}: {
  method: "GET" | "POST" | "DELETE" | "PUT" | "PATCH";
}) {
  const colours: Record<string, string> = {
    GET: "bg-emerald-100 text-emerald-800 dark:bg-emerald-900/40 dark:text-emerald-300",
    POST: "bg-blue-100 text-blue-800 dark:bg-blue-900/40 dark:text-blue-300",
    DELETE: "bg-red-100 text-red-800 dark:bg-red-900/40 dark:text-red-300",
    PUT: "bg-violet-100 text-violet-800 dark:bg-violet-900/40 dark:text-violet-300",
    PATCH:
      "bg-orange-100 text-orange-800 dark:bg-orange-900/40 dark:text-orange-300",
  };
  return (
    <span
      className={`inline-block rounded px-2 py-0.5 font-mono text-xs font-bold uppercase ${colours[method]}`}
    >
      {method}
    </span>
  );
}

function Code({ children }: { children: React.ReactNode }) {
  return (
    <code className="rounded bg-neutral-100 px-1.5 py-0.5 font-mono text-xs text-neutral-800 dark:bg-neutral-800 dark:text-neutral-200">
      {children}
    </code>
  );
}

function Pre({ children }: { children: string }) {
  return (
    <pre className="overflow-x-auto rounded-lg bg-neutral-100 p-4 text-xs text-neutral-800 dark:bg-neutral-900 dark:text-neutral-200">
      {children}
    </pre>
  );
}

interface Param {
  name: string;
  type: string;
  required?: boolean;
  description: string;
}

function ParamsTable({ params }: { params: Param[] }) {
  return (
    <div className="overflow-x-auto rounded-lg border border-neutral-200 dark:border-neutral-800">
      <table className="w-full min-w-[32rem] border-collapse text-left text-sm">
        <thead>
          <tr className="border-b border-neutral-200 bg-neutral-50 dark:border-neutral-800 dark:bg-neutral-800/50 text-xs uppercase tracking-wide text-neutral-500">
            <th className="px-3 py-2 font-semibold">Parameter</th>
            <th className="px-3 py-2 font-semibold">Type</th>
            <th className="px-3 py-2 font-semibold">Required</th>
            <th className="px-3 py-2 font-semibold">Description</th>
          </tr>
        </thead>
        <tbody className="text-neutral-700 dark:text-neutral-300">
          {params.map((p) => (
            <tr
              key={p.name}
              className="border-b border-neutral-100 last:border-b-0 dark:border-neutral-800/60"
            >
              <td className="px-3 py-2">
                <Code>{p.name}</Code>
              </td>
              <td className="px-3 py-2 font-mono text-xs text-neutral-500 dark:text-neutral-400">
                {p.type}
              </td>
              <td className="px-3 py-2 text-xs">
                {p.required ? (
                  <span className="text-amber-600 dark:text-amber-400">
                    required
                  </span>
                ) : (
                  <span className="text-neutral-400">optional</span>
                )}
              </td>
              <td className="px-3 py-2 text-xs">{p.description}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

interface Endpoint {
  id: string;
  method: "GET" | "POST";
  path: string;
  summary: string;
  description?: string;
  queryParams?: Param[];
  pathParams?: Param[];
  bodyParams?: Param[];
  responseSchema: string;
  exampleResponse: string;
}

const BASE_URL = "https://vinylscrape.cfb.wtf";

const ENDPOINTS: Endpoint[] = [
  {
    id: "list-vinyl",
    method: "GET",
    path: "/api/v1/vinyl",
    summary: "List / search vinyl",
    description:
      "Returns a paginated list of vinyl records. Supports full-text search, filtering, and sorting.",
    queryParams: [
      {
        name: "q",
        type: "string",
        description: "Full-text search across artist and title fields.",
      },
      {
        name: "genre",
        type: "string",
        description: "Comma-separated genre slugs to filter by.",
      },
      {
        name: "source",
        type: "string",
        description: "Comma-separated shop names to filter by.",
      },
      {
        name: "in_stock",
        type: "boolean",
        description: "When true, only records currently in stock are returned.",
      },
      {
        name: "price_min",
        type: "number (≥0)",
        description: "Minimum price filter (inclusive).",
      },
      {
        name: "price_max",
        type: "number (≥0)",
        description: "Maximum price filter (inclusive).",
      },
      {
        name: "condition",
        type: "string",
        description:
          "Goldmine condition grade (e.g. NM, VG+, VG, G+, G, F, P).",
      },
      {
        name: "sort",
        type: "enum",
        description:
          "Sort order: price_asc, price_desc, date (newest first), or title. Defaults to date.",
      },
      {
        name: "page",
        type: "integer (≥1)",
        description: "Page number. Defaults to 1.",
      },
      {
        name: "per_page",
        type: "integer (1–100)",
        description: "Items per page. Defaults to 24.",
      },
    ],
    responseSchema: `{
  "items": VinylListItem[],
  "total": integer,
  "page": integer,
  "per_page": integer,
  "pages": integer
}`,
    exampleResponse: `{
  "items": [
    {
      "id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
      "title": "Kind of Blue",
      "artist": "Miles Davis",
      "image_url": "https://...",
      "year": 1959,
      "genres": ["jazz"],
      "min_price": "45.00",
      "currency": "GEL",
      "in_stock": true,
      "source_count": 2
    }
  ],
  "total": 1,
  "page": 1,
  "per_page": 24,
  "pages": 1
}`,
  },
  {
    id: "get-vinyl",
    method: "GET",
    path: "/api/v1/vinyl/{vinyl_id}",
    summary: "Get vinyl detail",
    description:
      "Returns full metadata for a single vinyl record, including all shop listings and tracklist.",
    pathParams: [
      {
        name: "vinyl_id",
        type: "UUID",
        required: true,
        description: "UUID of the vinyl record.",
      },
    ],
    responseSchema: `{
  "id": UUID,
  "title": string,
  "artist": string,
  "label": string | null,
  "catalog_number": string | null,
  "year": integer | null,
  "condition": string | null,
  "image_url": string | null,
  "musicbrainz_id": string | null,
  "youtube_url": string | null,
  "created_at": datetime,
  "updated_at": datetime,
  "genres": string[],
  "sources": VinylSourceOut[],
  "tracklist": TrackOut[]
}`,
    exampleResponse: `{
  "id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "title": "Kind of Blue",
  "artist": "Miles Davis",
  "label": "Columbia",
  "catalog_number": "CS 8163",
  "year": 1959,
  "condition": "VG+",
  "image_url": "https://...",
  "musicbrainz_id": "2ee56f69-...",
  "youtube_url": "https://www.youtube.com/watch?v=...",
  "created_at": "2024-01-01T00:00:00Z",
  "updated_at": "2024-06-01T12:00:00Z",
  "genres": ["jazz"],
  "sources": [
    {
      "source_name": "morevi.ge",
      "external_url": "https://morevi.ge/...",
      "price": "45.00",
      "currency": "GEL",
      "in_stock": true,
      "scraped_at": "2024-06-01T10:00:00Z"
    }
  ],
  "tracklist": [
    { "position": "A1", "title": "So What", "duration": "9:22" }
  ]
}`,
  },
  {
    id: "list-genres",
    method: "GET",
    path: "/api/v1/genres",
    summary: "List genres",
    description:
      "Returns all genres with vinyl counts. Accepts the same filter parameters as the vinyl list endpoint so counts reflect the current filter context.",
    queryParams: [
      {
        name: "q",
        type: "string",
        description: "Search query (same as vinyl list).",
      },
      {
        name: "source",
        type: "string",
        description: "Source filter (same as vinyl list).",
      },
      {
        name: "in_stock",
        type: "boolean",
        description: "In-stock filter (same as vinyl list).",
      },
      {
        name: "genre",
        type: "string",
        description: "Already-selected genre slugs (for cross-count).",
      },
      {
        name: "condition",
        type: "string",
        description: "Condition filter (same as vinyl list).",
      },
    ],
    responseSchema: `GenreOut[] — array of:
{
  "id": UUID,
  "name": string,
  "slug": string,
  "vinyl_count": integer
}`,
    exampleResponse: `[
  { "id": "...", "name": "Jazz", "slug": "jazz", "vinyl_count": 182 },
  { "id": "...", "name": "Rock", "slug": "rock", "vinyl_count": 97 }
]`,
  },
  {
    id: "list-sources",
    method: "GET",
    path: "/api/v1/sources",
    summary: "List sources (shops)",
    description: "Returns all configured shop sources.",
    responseSchema: `SourceOut[] — array of:
{
  "id": UUID,
  "name": string,
  "base_url": string,
  "enabled": boolean,
  "last_scraped_at": datetime | null
}`,
    exampleResponse: `[
  {
    "id": "...",
    "name": "morevi.ge",
    "base_url": "https://morevi.ge",
    "enabled": true,
    "last_scraped_at": "2024-06-01T10:00:00Z"
  }
]`,
  },
  {
    id: "stats",
    method: "GET",
    path: "/api/v1/stats",
    summary: "Catalog statistics",
    description:
      "Returns high-level statistics: total records, in-stock count, active sources, top genres, and last scrape time.",
    responseSchema: `{
  "total_vinyls": integer,
  "in_stock": integer,
  "sources": integer,
  "top_genres": { [genre: string]: integer },
  "last_updated_at": datetime | null
}`,
    exampleResponse: `{
  "total_vinyls": 3840,
  "in_stock": 2150,
  "sources": 2,
  "top_genres": {
    "rock": 720,
    "jazz": 480,
    "classical": 310
  },
  "last_updated_at": "2024-06-01T10:00:00Z"
}`,
  },
];

/* ─── page ──────────────────────────────────────────────────── */

export default function ApiDocsPage() {
  return (
    <div className="max-w-4xl mx-auto px-4 py-10 sm:py-14">
      {/* Header */}
      <div className="mb-10">
        <p className="mb-3 inline-block rounded-full bg-amber-100 px-3 py-1 text-xs font-semibold uppercase tracking-widest text-amber-700 dark:bg-amber-950/40 dark:text-amber-300">
          Docs
        </p>
        <h1 className="text-3xl font-bold tracking-tight sm:text-4xl">
          API Reference
        </h1>
        <p className="mt-3 text-neutral-600 dark:text-neutral-400 sm:text-lg">
          All endpoints are available at{" "}
          <Code>{BASE_URL}/api/v1</Code>. Responses are JSON.
        </p>
      </div>

      {/* Quick nav */}
      <nav className="mb-10 rounded-lg border border-neutral-200 bg-neutral-50 p-4 dark:border-neutral-800 dark:bg-neutral-800/30 sm:p-5">
        <h2 className="mb-3 text-xs font-semibold uppercase tracking-wide text-neutral-500">
          Endpoints
        </h2>
        <ul className="space-y-1.5 text-sm">
          {ENDPOINTS.map((ep) => (
            <li key={ep.id} className="flex items-center gap-2">
              <Badge method={ep.method} />
              <a
                href={`#${ep.id}`}
                className="font-mono text-neutral-700 hover:text-amber-600 dark:text-neutral-300 dark:hover:text-amber-400"
              >
                {ep.path}
              </a>
            </li>
          ))}
        </ul>
      </nav>

      {/* Endpoint sections */}
      <div className="space-y-8">
        {ENDPOINTS.map((ep) => (
          <section key={ep.id} id={ep.id} className="scroll-mt-6 rounded-lg border border-neutral-200 p-5 dark:border-neutral-800 sm:p-6">
            <div className="mb-4 flex flex-wrap items-center gap-3">
              <Badge method={ep.method} />
              <Code>{ep.path}</Code>
            </div>
            <h2 className="mb-2 text-xl font-semibold text-foreground">{ep.summary}</h2>
            {ep.description && (
              <p className="mb-4 text-sm text-neutral-600 dark:text-neutral-400">
                {ep.description}
              </p>
            )}

            {ep.pathParams && ep.pathParams.length > 0 && (
              <div className="mb-4">
                <h3 className="mb-2 text-sm font-semibold uppercase tracking-wide text-neutral-500">
                  Path parameters
                </h3>
                <ParamsTable params={ep.pathParams} />
              </div>
            )}

            {ep.queryParams && ep.queryParams.length > 0 && (
              <div className="mb-4">
                <h3 className="mb-2 text-sm font-semibold uppercase tracking-wide text-neutral-500">
                  Query parameters
                </h3>
                <ParamsTable params={ep.queryParams} />
              </div>
            )}

            {ep.bodyParams && ep.bodyParams.length > 0 && (
              <div className="mb-4">
                <h3 className="mb-2 text-sm font-semibold uppercase tracking-wide text-neutral-500">
                  Request body (JSON)
                </h3>
                <ParamsTable params={ep.bodyParams} />
              </div>
            )}

            <div className="mb-3">
              <h3 className="mb-2 text-sm font-semibold uppercase tracking-wide text-neutral-500">
                Response schema
              </h3>
              <Pre>{ep.responseSchema}</Pre>
            </div>

            <div>
              <h3 className="mb-2 text-sm font-semibold uppercase tracking-wide text-neutral-500">
                Example response
              </h3>
              <Pre>{ep.exampleResponse}</Pre>
            </div>
          </section>
        ))}
      </div>

      {/* Footer */}
      <div className="mt-14 flex flex-col gap-3 border-t border-neutral-200 pt-8 dark:border-neutral-800 sm:flex-row">
        <Link
          href="/"
          className="rounded-lg bg-amber-500 px-5 py-3 text-center text-sm font-medium text-white transition-colors hover:bg-amber-600"
        >
          Browse catalog
        </Link>
        <Link
          href="/about"
          className="rounded-lg border border-neutral-300 px-5 py-3 text-center text-sm font-medium text-neutral-700 transition-colors hover:bg-neutral-100 dark:border-neutral-700 dark:text-neutral-300 dark:hover:bg-neutral-800"
        >
          About VinylScrape
        </Link>
      </div>
    </div>
  );
}
