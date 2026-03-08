"use client";

import { useQuery } from "@tanstack/react-query";
import Image from "next/image";
import Link from "next/link";
import { getVinyl } from "@/lib/api";
import PriceTag from "@/components/PriceTag";
import YouTubeEmbed from "@/components/YouTubeEmbed";
import AddToCartButton from "@/components/AddToCartButton";
import ConditionBadge from "@/components/ConditionBadge";
import type { TrackOut, VinylDetail } from "@/types/vinyl";

const RETROMANIA_WARNING =
  "Retromania.ge does not report availability status, you should check if items available";

const VODKAST_WARNING =
  "Vodkast.ge does not report availability status, you should check if items available";

function compareTrackPositions(a: string, b: string) {
  const parsePosition = (position: string) => {
    const value = position.trim().toUpperCase();
    const match = value.match(/^([A-Z]+)?\s*(\d+)(?:\s*[.-]\s*(\d+))?$/);

    if (!match) {
      return {
        side: "",
        index: Number.MAX_SAFE_INTEGER,
        subIndex: Number.MAX_SAFE_INTEGER,
        fallback: value,
      };
    }

    return {
      side: match[1] ?? "",
      index: Number(match[2]),
      subIndex: match[3] ? Number(match[3]) : 0,
      fallback: value,
    };
  };

  const left = parsePosition(a);
  const right = parsePosition(b);

  return (
    left.side.localeCompare(right.side) ||
    left.index - right.index ||
    left.subIndex - right.subIndex ||
    left.fallback.localeCompare(right.fallback)
  );
}

function sortTracklist(tracklist: TrackOut[]) {
  return [...tracklist].sort((a, b) =>
    compareTrackPositions(a.position, b.position),
  );
}

export default function VinylDetailClient({
  id,
  initialData,
}: {
  id: string;
  initialData: VinylDetail;
}) {
  const { data: vinyl } = useQuery({
    queryKey: ["vinyl", id],
    queryFn: () => getVinyl(id),
    initialData,
  });
  const sortedTracklist = vinyl ? sortTracklist(vinyl.tracklist) : [];
  const hasRetromaniaSource =
    vinyl?.sources.some((source) => source.source_name.toLowerCase() === "retromania.ge") ?? false;
  const hasVodkastSource =
    vinyl?.sources.some((source) => source.source_name.toLowerCase() === "vodkast.ge") ?? false;

  const availabilityWarning = hasRetromaniaSource
    ? RETROMANIA_WARNING
    : hasVodkastSource
      ? VODKAST_WARNING
      : undefined;

  return (
    <div className="max-w-5xl mx-auto px-4 py-6 sm:py-8">
      <Link
        href="/"
        className="text-sm text-neutral-500 hover:text-amber-500 transition-colors mb-6 inline-block"
      >
        &larr; Back to catalog
      </Link>

      <div className="flex flex-col md:flex-row gap-8">
        {/* Cover art */}
        <div className="w-full md:w-96 shrink-0">
          <div className="relative aspect-square rounded-xl overflow-hidden bg-neutral-100 dark:bg-neutral-800">
            {vinyl.image_url ? (
              <Image
                src={vinyl.image_url}
                alt={`${vinyl.artist} - ${vinyl.title}`}
                fill
                unoptimized
                className="object-cover"
                sizes="(max-width: 768px) 100vw, 384px"
                priority
              />
            ) : (
              <div className="flex items-center justify-center h-full text-neutral-400 text-6xl">
                ♫
              </div>
            )}
          </div>
        </div>

        {/* Details */}
        <div className="flex-1 space-y-4">
          <div>
            <p className="text-lg text-neutral-500 dark:text-neutral-400">
              {vinyl.artist}
            </p>
            <h1 className="text-2xl sm:text-3xl font-bold">{vinyl.title}</h1>
          </div>

          {/* Meta */}
          <dl className="grid grid-cols-1 gap-x-6 gap-y-2 text-sm sm:grid-cols-2">
            {vinyl.label && (
              <>
                <dt className="text-neutral-500">Label</dt>
                <dd>{vinyl.label}</dd>
              </>
            )}
            {vinyl.catalog_number && (
              <>
                <dt className="text-neutral-500">Cat#</dt>
                <dd>{vinyl.catalog_number}</dd>
              </>
            )}
            {vinyl.year && (
              <>
                <dt className="text-neutral-500">Year</dt>
                <dd>{vinyl.year}</dd>
              </>
            )}
            {vinyl.condition && (
              <>
                <dt className="text-neutral-500">Condition</dt>
                <dd>
                  <ConditionBadge condition={vinyl.condition} />
                </dd>
              </>
            )}
            {vinyl.musicbrainz_id && (
              <>
                <dt className="text-neutral-500">MusicBrainz</dt>
                <dd>
                  <a
                    href={`https://musicbrainz.org/release/${vinyl.musicbrainz_id}`}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-amber-500 hover:underline"
                  >
                    {vinyl.musicbrainz_id}
                  </a>
                </dd>
              </>
            )}
          </dl>

          {/* Genre tags */}
          {vinyl.genres.length > 0 && (
            <div className="flex flex-wrap gap-1.5">
              {vinyl.genres.map((genre) => {
                const slug = genre.toLowerCase().trim().replace(/[^\w\s-]/g, "").replace(/[-\s]+/g, "-");
                return (
                  <Link
                    key={genre}
                    href={`/?genre=${encodeURIComponent(slug)}`}
                    className="text-xs px-3 py-1 rounded-full bg-neutral-100 dark:bg-neutral-800 text-neutral-600 dark:text-neutral-300 hover:bg-amber-100 hover:text-amber-700 dark:hover:bg-amber-900/30 dark:hover:text-amber-400 transition-colors"
                  >
                    {genre}
                  </Link>
                );
              })}
            </div>
          )}

          {/* Add to cart */}
          <AddToCartButton
            item={{
              id: vinyl.id,
              title: vinyl.title,
              artist: vinyl.artist,
              image_url: vinyl.image_url,
              price: vinyl.sources.length > 0
                ? Math.min(...vinyl.sources.map((s) => s.price))
                : null,
              currency: vinyl.sources[0]?.currency ?? "GEL",
            }}
            warningMessage={availabilityWarning}
          />

          {/* Price comparison */}
          {vinyl.sources.length > 0 && (
            <div>
              <h2 className="font-semibold mb-2">Prices</h2>
              <div className="overflow-hidden rounded-lg border border-neutral-200 dark:border-neutral-800">
                <div className="overflow-x-auto">
                <table className="w-full min-w-[36rem] text-sm">
                  <thead className="bg-neutral-50 dark:bg-neutral-800/50">
                    <tr>
                      <th className="text-left px-4 py-2 font-medium">Shop</th>
                      <th className="text-left px-4 py-2 font-medium">Price</th>
                      <th className="text-left px-4 py-2 font-medium">Status</th>
                      <th className="text-right px-4 py-2 font-medium" />
                    </tr>
                  </thead>
                  <tbody>
                    {vinyl.sources.map((src, i) => (
                      <tr
                        key={i}
                        className="border-t border-neutral-200 dark:border-neutral-800"
                      >
                        <td className="px-4 py-2">{src.source_name}</td>
                        <td className="px-4 py-2">
                          <PriceTag price={src.price} currency={src.currency} />
                        </td>
                        <td className="px-4 py-2">
                          {src.in_stock ? (
                            <span className="text-green-600 dark:text-green-400">
                              In Stock
                            </span>
                          ) : (
                            <span className="text-red-500">Sold Out</span>
                          )}
                        </td>
                        <td className="px-4 py-2 text-right">
                          <a
                            href={src.external_url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="text-amber-500 hover:underline"
                          >
                            View &rarr;
                          </a>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
                </div>
              </div>
            </div>
          )}

          {/* Tracklist */}
          {vinyl.tracklist.length > 0 && (
            <div>
              <h2 className="font-semibold mb-2">Tracklist</h2>
              <div className="overflow-hidden rounded-lg border border-neutral-200 dark:border-neutral-800">
                <div className="overflow-x-auto">
                <table className="w-full min-w-[28rem] text-sm">
                  <tbody>
                    {sortedTracklist.map((track, i) => (
                      <tr
                        key={i}
                        className="border-t first:border-t-0 border-neutral-200 dark:border-neutral-800"
                      >
                        <td className="px-4 py-2 w-12 text-neutral-400 font-mono">
                          {track.position}
                        </td>
                        <td className="px-4 py-2">{track.title}</td>
                        <td className="px-4 py-2 text-right">
                          {track.youtube_url && (
                            <a
                              href={track.youtube_url}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="text-red-500 hover:underline text-xs"
                            >
                              YouTube
                            </a>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
                </div>
              </div>
            </div>
          )}

          {/* YouTube embed */}
          {vinyl.youtube_url && (
            <div>
              <h2 className="font-semibold mb-2">Preview</h2>
              <YouTubeEmbed url={vinyl.youtube_url} />
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
