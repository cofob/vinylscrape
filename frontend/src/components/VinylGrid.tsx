import type { VinylListItem } from "@/types/vinyl";
import VinylCard from "./VinylCard";

interface VinylGridProps {
  items: VinylListItem[];
  loading?: boolean;
  loadingMore?: boolean;
  loadingMoreCount?: number;
}

function SkeletonCard({ index }: { index: number }) {
  return (
    <div
      key={index}
      className="overflow-hidden rounded-xl border border-neutral-200 animate-pulse dark:border-neutral-800"
    >
      <div className="aspect-square bg-neutral-200 dark:bg-neutral-800" />
      <div className="space-y-2 p-3">
        <div className="h-3 w-2/3 rounded bg-neutral-200 dark:bg-neutral-700" />
        <div className="h-4 w-full rounded bg-neutral-200 dark:bg-neutral-700" />
        <div className="h-3 w-1/3 rounded bg-neutral-200 dark:bg-neutral-700" />
      </div>
    </div>
  );
}

export default function VinylGrid({
  items,
  loading,
  loadingMore = false,
  loadingMoreCount = 8,
}: VinylGridProps) {
  if (loading) {
    return (
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 sm:gap-4 lg:grid-cols-4 xl:grid-cols-5">
        {Array.from({ length: 12 }).map((_, i) => (
          <SkeletonCard key={i} index={i} />
        ))}
      </div>
    );
  }

  if (items.length === 0) {
    return (
      <div className="text-center py-16 text-neutral-500">
        <p className="text-5xl mb-4">♫</p>
        <p className="text-lg">No vinyl records found</p>
        <p className="text-sm mt-1">Try adjusting your search or filters</p>
      </div>
    );
  }

  return (
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 sm:gap-4 lg:grid-cols-4 xl:grid-cols-5">
      {items.map((vinyl) => (
        <VinylCard key={vinyl.id} vinyl={vinyl} preloadImage />
      ))}
      {loadingMore &&
        Array.from({ length: loadingMoreCount }).map((_, i) => (
          <SkeletonCard key={`loading-more-${i}`} index={i} />
        ))}
    </div>
  );
}
