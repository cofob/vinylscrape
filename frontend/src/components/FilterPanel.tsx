"use client";

import { useState } from "react";
import type { GenreOut, SourceOut } from "@/types/vinyl";

const CONDITIONS = [
  { grade: "M",   label: "Mint" },
  { grade: "NM",  label: "Near Mint" },
  { grade: "VG+", label: "Very Good Plus" },
  { grade: "VG",  label: "Very Good" },
  { grade: "G+",  label: "Good Plus" },
  { grade: "G",   label: "Good" },
  { grade: "F",   label: "Fair" },
  { grade: "P",   label: "Poor" },
];

interface FilterPanelProps {
  genres: GenreOut[];
  sources: SourceOut[];
  selectedGenres: string[];
  selectedSources: string[];
  inStockOnly: boolean;
  condition: string;
  sort: string;
  onGenreToggle: (slug: string) => void;
  onGenreClear: () => void;
  onSourceToggle: (name: string) => void;
  onSourceClear: () => void;
  onInStockChange: (inStock: boolean) => void;
  onConditionChange: (condition: string) => void;
  onSortChange: (sort: string) => void;
}

export default function FilterPanel({
  genres,
  sources,
  selectedGenres,
  selectedSources,
  inStockOnly,
  condition,
  sort,
  onGenreToggle,
  onGenreClear,
  onSourceToggle,
  onSourceClear,
  onInStockChange,
  onConditionChange,
  onSortChange,
}: FilterPanelProps) {
  const [isExpanded, setIsExpanded] = useState(false);

  return (
    <div className="rounded-2xl border border-neutral-200 bg-white p-4 dark:border-neutral-800 dark:bg-neutral-900 lg:border-0 lg:bg-transparent lg:p-0">
      <div className="mb-4 flex items-center justify-between lg:hidden">
        <div>
          <p className="text-sm font-semibold">Filters</p>
          <p className="text-xs text-neutral-500 dark:text-neutral-400">
            Refine by shop, condition, and genre
          </p>
        </div>
        <button
          onClick={() => setIsExpanded((value) => !value)}
          className="rounded-lg border border-neutral-300 px-3 py-2 text-sm transition-colors hover:bg-neutral-100 dark:border-neutral-700 dark:hover:bg-neutral-800"
        >
          {isExpanded ? "Hide" : "Show"}
        </button>
      </div>

      <div className={`${isExpanded ? "block" : "hidden"} space-y-4 lg:block`}>
      {/* Sort */}
      <div>
        <label className="block text-sm font-medium text-neutral-600 dark:text-neutral-400 mb-1">
          Sort by
        </label>
        <select
          value={sort}
          onChange={(e) => onSortChange(e.target.value)}
          className="w-full px-3 py-2 rounded-lg border border-neutral-300 dark:border-neutral-700 bg-white dark:bg-neutral-900 text-sm"
        >
          <option value="date">Newest first</option>
          <option value="title">Title A-Z</option>
          <option value="price_asc">Price: Low to High</option>
          <option value="price_desc">Price: High to Low</option>
        </select>
      </div>

      {/* In Stock Toggle */}
      <label className="flex items-center gap-2 cursor-pointer">
        <input
          type="checkbox"
          checked={inStockOnly}
          onChange={(e) => onInStockChange(e.target.checked)}
          className="rounded border-neutral-300 text-amber-600 focus:ring-amber-500"
        />
        <span className="text-sm">In stock only</span>
      </label>

      {/* Condition */}
      <div>
        <label className="block text-sm font-medium text-neutral-600 dark:text-neutral-400 mb-1">
          Min. condition
        </label>
        <select
          value={condition}
          onChange={(e) => onConditionChange(e.target.value)}
          className="w-full px-3 py-2 rounded-lg border border-neutral-300 dark:border-neutral-700 bg-white dark:bg-neutral-900 text-sm"
        >
          <option value="">Any</option>
          {CONDITIONS.map(({ grade, label }) => (
            <option key={grade} value={grade}>
              {grade} or better ({label})
            </option>
          ))}
        </select>
      </div>

      {/* Genres */}
      {genres.length > 0 && (
        <div>
          <div className="flex items-center justify-between mb-2">
            <label className="block text-sm font-medium text-neutral-600 dark:text-neutral-400">
              Genres
            </label>
            {selectedGenres.length > 0 && (
              <button
                onClick={onGenreClear}
                className="text-xs text-amber-600 hover:text-amber-700 dark:text-amber-400 dark:hover:text-amber-300"
              >
                Clear
              </button>
            )}
          </div>
          <div className="flex flex-wrap gap-1.5">
            {genres.map((genre) => {
              const isSelected = selectedGenres.includes(genre.slug);
              return (
                <button
                  key={genre.slug}
                  onClick={() => onGenreToggle(genre.slug)}
                  className={`text-xs px-3 py-1 rounded-full border transition-colors ${
                    isSelected
                      ? "bg-amber-500 text-white border-amber-500"
                      : "border-neutral-300 dark:border-neutral-700 hover:border-amber-400"
                  }`}
                >
                  {genre.name}{" "}
                  <span className="opacity-60">({genre.vinyl_count})</span>
                </button>
              );
            })}
          </div>
        </div>
      )}

      {/* Sources */}
      {sources.length > 0 && (
        <div>
          <div className="flex items-center justify-between mb-2">
            <label className="block text-sm font-medium text-neutral-600 dark:text-neutral-400">
              Shops
            </label>
            {selectedSources.length > 0 && (
              <button
                onClick={onSourceClear}
                className="text-xs text-amber-600 hover:text-amber-700 dark:text-amber-400 dark:hover:text-amber-300"
              >
                Clear
              </button>
            )}
          </div>
          <div className="space-y-1">
            <label className="flex items-center gap-2 cursor-pointer">
              <input
                type="checkbox"
                checked={selectedSources.length === 0}
                onChange={onSourceClear}
                className="rounded border-neutral-300 text-amber-600 focus:ring-amber-500"
              />
              <span className="text-sm">All shops</span>
            </label>
            {sources.map((source) => (
              <label
                key={source.id}
                className="flex items-center gap-2 cursor-pointer"
              >
                <input
                  type="checkbox"
                  checked={selectedSources.includes(source.name)}
                  onChange={() => onSourceToggle(source.name)}
                  className="rounded border-neutral-300 text-amber-600 focus:ring-amber-500"
                />
                <span className="text-sm">{source.name}</span>
              </label>
            ))}
          </div>
        </div>
      )}
      </div>
    </div>
  );
}
