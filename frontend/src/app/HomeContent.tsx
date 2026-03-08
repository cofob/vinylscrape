"use client";

import { useEffect, useMemo, useRef } from "react";
import { useInfiniteQuery, useQuery } from "@tanstack/react-query";
import { useQueryState, parseAsBoolean, parseAsString } from "nuqs";
import { searchVinyls, getGenres, getSources, getStats } from "@/lib/api";
import SearchBar from "@/components/SearchBar";
import VinylGrid from "@/components/VinylGrid";
import FilterPanel from "@/components/FilterPanel";
import { useYouTubePlayer } from "@/lib/youtube-player";

function formatLastUpdated(value: string | null) {
  if (!value) {
    return null;
  }

  const date = new Date(value);

  if (Number.isNaN(date.getTime())) {
    return null;
  }

  return new Intl.DateTimeFormat(undefined, {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(date);
}

export default function HomeContent() {
  const [q, setQ] = useQueryState("q", parseAsString.withDefault(""));
  const [genreParam, setGenreParam] = useQueryState("genre", parseAsString.withDefault(""));
  const [source, setSource] = useQueryState("source", parseAsString.withDefault(""));
  const [inStock, setInStock] = useQueryState("in_stock", parseAsBoolean.withDefault(true));
  const [condition, setCondition] = useQueryState("condition", parseAsString.withDefault(""));
  const [sort, setSort] = useQueryState("sort", parseAsString.withDefault("date"));
  const loadMoreRef = useRef<HTMLDivElement | null>(null);

  // Parse comma-separated genre string into array
  const selectedGenres = genreParam ? genreParam.split(",").filter(Boolean) : [];
  const selectedSources = source ? source.split(",").filter(Boolean) : [];

  const toggleGenre = (slug: string) => {
    const next = selectedGenres.includes(slug)
      ? selectedGenres.filter((s) => s !== slug)
      : [...selectedGenres, slug];
    setGenreParam(next.length > 0 ? next.join(",") : "");
  };

  const clearGenres = () => {
    setGenreParam("");
  };

  const toggleSource = (name: string) => {
    const next = selectedSources.includes(name)
      ? selectedSources.filter((sourceName) => sourceName !== name)
      : [...selectedSources, name];
    setSource(next.length > 0 ? next.join(",") : "");
  };

  const clearSources = () => {
    setSource("");
  };

  const { data: genresData } = useQuery({
    queryKey: ["genres", q, source, inStock, condition],
    queryFn: () =>
      getGenres({
        q: q || undefined,
        source: selectedSources.length > 0 ? selectedSources : undefined,
        in_stock: inStock || undefined,
        condition: condition || undefined,
      }),
  });
  const visibleGenres = (genresData ?? []).filter((genre) => genre.vinyl_count >= 2);

  const { data: sourcesData } = useQuery({
    queryKey: ["sources"],
    queryFn: getSources,
  });

  const { data: statsData, isPending: statsPending } = useQuery({
    queryKey: ["stats"],
    queryFn: getStats,
  });

  const lastUpdatedLabel = formatLastUpdated(statsData?.last_updated_at ?? null);

  const {
    data,
    isLoading,
    isFetchingNextPage,
    hasNextPage,
    fetchNextPage,
  } = useInfiniteQuery({
    queryKey: ["vinyls", q, genreParam, source, inStock, condition, sort],
    initialPageParam: 1,
    queryFn: ({ pageParam }) =>
      searchVinyls({
        q: q || undefined,
        genre: selectedGenres.length > 0 ? selectedGenres : undefined,
        source: selectedSources.length > 0 ? selectedSources : undefined,
        in_stock: inStock || undefined,
        condition: condition || undefined,
        sort: sort || undefined,
        page: pageParam,
        per_page: 48,
      }),
    getNextPageParam: (lastPage) =>
      lastPage.page < lastPage.pages ? lastPage.page + 1 : undefined,
  });

  const items = useMemo(
    () => data?.pages.flatMap((page) => page.items) ?? [],
    [data],
  );
  const total = data?.pages[0]?.total ?? 0;
  const loadedCount = items.length;

  // Keep the YouTube player playlist in sync with the loaded catalog items.
  const { setPlaylist } = useYouTubePlayer();
  useEffect(() => {
    const playlist = items
      .filter((v) => v.youtube_url)
      .map((v) => ({
        url: v.youtube_url!,
        title: `${v.artist} — ${v.title}`,
      }));
    setPlaylist(playlist);
  }, [items, setPlaylist]);

  useEffect(() => {
    if (!loadMoreRef.current || !hasNextPage || isFetchingNextPage) {
      return;
    }

    const observer = new IntersectionObserver(
      (entries) => {
        if (entries[0]?.isIntersecting) {
          fetchNextPage();
        }
      },
      { rootMargin: "800px 0px" },
    );

    observer.observe(loadMoreRef.current);

    return () => observer.disconnect();
  }, [fetchNextPage, hasNextPage, isFetchingNextPage]);

  return (
    <div className="max-w-7xl mx-auto px-4 py-6 sm:py-8">
      {/* Hero / Search */}
      <div className="mb-6 text-center sm:mb-8">
        <h1 className="mb-2 text-3xl font-bold sm:text-4xl">
          Vinyl<span className="text-amber-500">Scrape</span>
        </h1>
        <p className="mb-4 text-sm text-neutral-500 dark:text-neutral-400 sm:mb-6 sm:text-base">
          Search vinyl records from Georgian shops
        </p>
        {statsPending ? (
          <div className="mb-4 flex justify-center">
            <div className="h-4 w-48 animate-pulse rounded bg-neutral-200 dark:bg-neutral-700" />
          </div>
        ) : lastUpdatedLabel ? (
          <p className="mb-4 text-xs text-neutral-500 dark:text-neutral-400 sm:text-sm">
            Last updated at {lastUpdatedLabel}
          </p>
        ) : null}
        <SearchBar value={q} onChange={setQ} />
      </div>

      <div className="flex flex-col gap-6 lg:flex-row lg:gap-8">
        {/* Sidebar filters */}
        <aside className="shrink-0 lg:w-72">
          <FilterPanel
            genres={visibleGenres}
            sources={sourcesData ?? []}
            selectedGenres={selectedGenres}
            selectedSources={selectedSources}
            inStockOnly={inStock}
            condition={condition}
            sort={sort}
            onGenreToggle={toggleGenre}
            onGenreClear={clearGenres}
            onSourceToggle={toggleSource}
            onSourceClear={clearSources}
            onInStockChange={setInStock}
            onConditionChange={setCondition}
            onSortChange={setSort}
          />
        </aside>

        {/* Main content */}
        <div className="flex-1">
          {/* Result count */}
          {isLoading ? (
            <div className="h-4 w-32 bg-neutral-200 dark:bg-neutral-800 rounded animate-pulse mb-4" />
          ) : data && (
            <p className="mb-4 text-sm text-neutral-500">
              {loadedCount} of {total} record{total !== 1 ? "s" : ""} loaded
            </p>
          )}

          <VinylGrid
            items={items}
            loading={isLoading}
            loadingMore={isFetchingNextPage}
            loadingMoreCount={48}
          />

          {!isLoading && items.length > 0 && (
            <div className="mt-8">
              <div ref={loadMoreRef} className="h-1 w-full" />
              {!hasNextPage && (
                <p className="text-center text-sm text-neutral-500">
                  You&apos;ve reached the end of the catalog
                </p>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
