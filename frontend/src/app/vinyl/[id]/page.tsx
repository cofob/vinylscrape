import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { getVinylServer } from "@/lib/api-server";
import VinylDetailClient from "./VinylDetailClient";

const CANONICAL_BASE = "https://vinylscrape.cfb.wtf";

export async function generateMetadata({
  params,
}: {
  params: Promise<{ id: string }>;
}): Promise<Metadata> {
  const { id } = await params;
  const vinyl = await getVinylServer(id);
  if (!vinyl) return { title: "Not Found" };

  const descParts = [
    vinyl.artist,
    vinyl.year ? `(${vinyl.year})` : null,
    vinyl.label ? `on ${vinyl.label}` : null,
    vinyl.genres.length > 0 ? `— ${vinyl.genres.join(", ")}` : null,
  ].filter(Boolean) as string[];
  const description = `Buy ${vinyl.title} by ${vinyl.artist}. ${descParts.join(" ")}. Compare prices from Georgian vinyl shops.`;
  const shortDesc = descParts.join(" ");

  const ogImages =
    vinyl.og_image_url
      ? [{ url: vinyl.og_image_url, width: 1200, height: 630 }]
      : vinyl.image_url
        ? [{ url: vinyl.image_url }]
        : [];

  const twitterImages =
    vinyl.og_image_url
      ? [vinyl.og_image_url]
      : vinyl.image_url
        ? [vinyl.image_url]
        : [];

  return {
    title: `${vinyl.artist} — ${vinyl.title}`,
    description,
    alternates: {
      canonical: `/vinyl/${vinyl.slug ?? id}`,
    },
    openGraph: {
      title: `${vinyl.artist} — ${vinyl.title}`,
      description: shortDesc,
      type: "music.album",
      url: `${CANONICAL_BASE}/vinyl/${vinyl.slug ?? id}`,
      images: ogImages,
      siteName: "VinylScrape",
    },
    twitter: {
      card: "summary_large_image",
      title: `${vinyl.artist} — ${vinyl.title}`,
      description: shortDesc,
      images: twitterImages,
    },
  };
}

export default async function VinylDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  const vinyl = await getVinylServer(id);
  if (!vinyl) {
    notFound();
  }

  // JSON-LD structured data: Product + MusicAlbum
  const productJsonLd = {
    "@context": "https://schema.org",
    "@type": "Product",
    name: vinyl.title,
    image: vinyl.image_url ?? undefined,
    description: `${vinyl.artist} — ${vinyl.title}`,
    brand: { "@type": "Brand", name: vinyl.artist },
    category: "Vinyl Records",
    offers: vinyl.sources.map((src) => ({
      "@type": "Offer",
      url: src.external_url,
      priceCurrency: src.currency,
      price: String(src.price),
      availability: src.in_stock
        ? "https://schema.org/InStock"
        : "https://schema.org/OutOfStock",
      seller: { "@type": "Organization", name: src.source_name },
    })),
  };

  const musicAlbumJsonLd = {
    "@context": "https://schema.org",
    "@type": "MusicAlbum",
    name: vinyl.title,
    byArtist: { "@type": "MusicGroup", name: vinyl.artist },
    datePublished: vinyl.year ? String(vinyl.year) : undefined,
    genre: vinyl.genres,
    image: vinyl.image_url ?? undefined,
    track:
      vinyl.tracklist.length > 0
        ? {
            "@type": "ItemList",
            itemListElement: vinyl.tracklist.map((t, i) => ({
              "@type": "MusicRecording",
              name: t.title,
              position: i + 1,
            })),
          }
        : undefined,
  };

  return (
    <>
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(productJsonLd) }}
      />
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(musicAlbumJsonLd) }}
      />
      <VinylDetailClient id={id} initialData={vinyl} />
    </>
  );
}
