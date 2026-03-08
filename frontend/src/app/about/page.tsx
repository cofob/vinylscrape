import type { Metadata } from "next";
import Link from "next/link";

export const metadata: Metadata = {
  title: "About",
  description:
    "Learn about VinylScrape, a vinyl record search aggregator for Georgian shops.",
  openGraph: {
    title: "About VinylScrape",
    description:
      "A unified search and price-comparison tool for vinyl records sold in Georgian shops.",
    images: [{ url: "/og/about.png", width: 1200, height: 630 }],
  },
  twitter: {
    card: "summary_large_image",
    title: "About VinylScrape",
    description:
      "A unified search and price-comparison tool for vinyl records sold in Georgian shops.",
    images: ["/og/about.png"],
  },
};

export default function AboutPage() {
  return (
    <div className="max-w-3xl mx-auto px-4 py-10 sm:py-14">
      {/* Hero */}
      <div className="mb-10">
        <p className="mb-3 inline-block rounded-full bg-amber-100 px-3 py-1 text-xs font-semibold uppercase tracking-widest text-amber-700 dark:bg-amber-950/40 dark:text-amber-300">
          About
        </p>
        <h1 className="text-3xl font-bold tracking-tight sm:text-4xl">
          Vinyl<span className="text-amber-500">Scrape</span>
        </h1>
        <p className="mt-4 text-neutral-600 dark:text-neutral-400 sm:text-lg">
          A unified search and price-comparison tool for vinyl records sold in
          Georgian shops.
        </p>
      </div>

      {/* What is VinylScrape */}
      <section className="mb-10 space-y-4 text-sm leading-relaxed text-neutral-700 dark:text-neutral-300 sm:text-base">
        <h2 className="text-lg font-semibold text-foreground sm:text-xl">
          What is VinylScrape?
        </h2>
        <p>
          VinylScrape automatically crawls Georgian record shops and aggregates
          their listings into a single, searchable catalog. Instead of visiting
          each shop individually, you can search, filter, and compare prices in
          one place.
        </p>
        <p>
          Every listing is enriched with metadata from{" "}
          <a
            href="https://musicbrainz.org"
            target="_blank"
            rel="noopener noreferrer"
            className="text-amber-600 hover:underline dark:text-amber-400"
          >
            MusicBrainz
          </a>
          : artist, label, catalog number, release year, tracklist, and a
          YouTube preview when available. Condition grades follow the standard
          Goldmine grading scale.
        </p>
      </section>

      {/* Features */}
      <section className="mb-10">
        <h2 className="mb-4 text-lg font-semibold text-foreground sm:text-xl">Features</h2>
        <ul className="space-y-3 text-sm text-neutral-700 dark:text-neutral-300 sm:text-base">
          {[
            {
              icon: "🔍",
              title: "Full-text search",
              desc: "Search across artist names and album titles from all shops at once.",
            },
            {
              icon: "🏷️",
              title: "Price comparison",
              desc: "See prices from every shop that stocks the same record side-by-side.",
            },
            {
              icon: "🎵",
              title: "Rich metadata",
              desc: "MusicBrainz-sourced tracklists, release years, labels, and catalog numbers.",
            },
            {
              icon: "▶️",
              title: "YouTube preview",
              desc: "Embedded preview player so you can listen before you buy.",
            },
            {
              icon: "🛒",
              title: "Multi-shop cart",
              desc: "Save records and compare your total across different shops.",
            },
            {
              icon: "📶",
              title: "Works offline",
              desc: "Installable as a Progressive Web App with offline support.",
            },
          ].map(({ icon, title, desc }) => (
            <li key={title} className="flex gap-3">
              <span className="mt-0.5 shrink-0 text-lg">{icon}</span>
              <span>
                <strong className="font-medium text-foreground">{title}:</strong>{" "}
                {desc}
              </span>
            </li>
          ))}
        </ul>
      </section>

      {/* Data freshness */}
      <section className="mb-10 space-y-3 text-sm leading-relaxed text-neutral-700 dark:text-neutral-300 sm:text-base">
        <h2 className="text-lg font-semibold text-foreground sm:text-xl">
          Data freshness
        </h2>
        <p>
          Shop listings are scraped on a regular schedule. The catalog home page
          shows the time of the last completed scrape. Prices and availability
          reflect the state of the shop at the time of the last crawl — always
          verify on the shop&apos;s own website before purchasing.
        </p>
      </section>

      {/* Open API */}
      <section className="mb-10 space-y-3 text-sm leading-relaxed text-neutral-700 dark:text-neutral-300 sm:text-base">
        <h2 className="text-lg font-semibold text-foreground sm:text-xl">
          Open API
        </h2>
        <p>
          VinylScrape exposes a public REST API. You can build your own tools on
          top of the same data.
        </p>
        <Link
          href="/docs/api"
          className="inline-block rounded-lg bg-amber-500 px-5 py-2.5 text-sm font-medium text-white transition-colors hover:bg-amber-600"
        >
          View API docs
        </Link>
      </section>

      {/* Footer CTA */}
      <div className="mt-12 flex flex-col gap-3 border-t border-neutral-200 pt-8 dark:border-neutral-800 sm:flex-row">
        <Link
          href="/"
          className="rounded-lg bg-amber-500 px-5 py-3 text-center text-sm font-medium text-white transition-colors hover:bg-amber-600"
        >
          Browse catalog
        </Link>
        <Link
          href="/docs/api"
          className="rounded-lg border border-neutral-300 px-5 py-3 text-center text-sm font-medium text-neutral-700 transition-colors hover:bg-neutral-100 dark:border-neutral-700 dark:text-neutral-300 dark:hover:bg-neutral-800"
        >
          API reference
        </Link>
      </div>
    </div>
  );
}
