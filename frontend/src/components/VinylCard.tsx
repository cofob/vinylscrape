"use client";

import Image from "next/image";
import Link from "next/link";
import type { VinylListItem } from "@/types/vinyl";
import PriceTag from "./PriceTag";
import AddToCartButton from "./AddToCartButton";
import { useYouTubePlayer } from "@/lib/youtube-player";

interface VinylCardProps {
  vinyl: VinylListItem;
  preloadImage?: boolean;
}

export default function VinylCard({ vinyl, preloadImage = false }: VinylCardProps) {
  const { play } = useYouTubePlayer();

  const handlePlay = (e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (vinyl.youtube_url) {
      play(vinyl.youtube_url, `${vinyl.artist} — ${vinyl.title}`);
    }
  };

  return (
    <Link
      href={`/vinyl/${vinyl.slug ?? vinyl.id}`}
      prefetch={false}
      className="group block rounded-xl border border-neutral-200 dark:border-neutral-800 bg-white dark:bg-neutral-900 overflow-hidden hover:shadow-lg transition-shadow"
    >
      {/* Cover art */}
      <div className="relative aspect-square bg-neutral-100 dark:bg-neutral-800">
        {vinyl.image_url ? (
          <Image
            src={vinyl.image_url}
            alt={`${vinyl.artist} - ${vinyl.title}`}
            fill
            preload={preloadImage}
            unoptimized
            className="object-cover group-hover:scale-105 transition-transform duration-300"
            sizes="(max-width: 640px) 100vw, (max-width: 1024px) 50vw, 25vw"
          />
        ) : (
          <div className="flex items-center justify-center h-full text-neutral-400 text-4xl">
            ♫
          </div>
        )}
        {!vinyl.in_stock && (
          <div className="absolute top-2 right-2 bg-neutral-900/80 text-white text-xs font-bold px-2 py-1 rounded">
            SOLD OUT
          </div>
        )}
        {/* Action buttons overlay — always visible on mobile, hover-only on sm+ */}
        <div className="absolute bottom-2 right-2 flex items-center gap-1.5 sm:opacity-0 sm:group-hover:opacity-100 transition-opacity">
          {vinyl.youtube_url && (
            <button
              onClick={handlePlay}
              title="Play"
              className="p-2.5 sm:p-1.5 rounded-lg transition-colors bg-neutral-100 dark:bg-neutral-800 text-neutral-500 hover:bg-red-100 hover:text-red-600 dark:hover:bg-red-900/30 dark:hover:text-red-400"
            >
              <svg
                xmlns="http://www.w3.org/2000/svg"
                viewBox="0 0 24 24"
                fill="currentColor"
                className="w-5 h-5 sm:w-4 sm:h-4"
              >
                <path d="M8 5v14l11-7z" />
              </svg>
            </button>
          )}
          <AddToCartButton
            compact
            item={{
              id: vinyl.id,
              title: vinyl.title,
              artist: vinyl.artist,
              image_url: vinyl.image_url,
              price: vinyl.min_price,
              currency: vinyl.currency,
            }}
          />
        </div>
      </div>

      {/* Info */}
      <div className="p-3 space-y-1">
        <p className="text-sm text-neutral-500 dark:text-neutral-400 truncate">
          {vinyl.artist}
        </p>
        <p className="font-medium truncate">{vinyl.title}</p>
        <div className="flex items-center justify-between pt-1">
          <PriceTag price={vinyl.min_price} currency={vinyl.currency} />
          {vinyl.source_count > 1 && (
            <span className="text-xs text-neutral-400">
              {vinyl.source_count} shops
            </span>
          )}
        </div>
        {vinyl.genres.length > 0 && (
          <div className="flex flex-wrap gap-1 pt-1">
            {vinyl.genres.slice(0, 3).map((genre) => (
              <span
                key={genre}
                className="text-xs px-2 py-0.5 rounded-full bg-neutral-100 dark:bg-neutral-800 text-neutral-600 dark:text-neutral-300"
              >
                {genre}
              </span>
            ))}
          </div>
        )}
      </div>
    </Link>
  );
}
