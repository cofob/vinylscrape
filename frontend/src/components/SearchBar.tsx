"use client";

import { useRef } from "react";

interface SearchBarProps {
  value: string;
  onChange: (value: string) => void;
}

export default function SearchBar({ value, onChange }: SearchBarProps) {
  const inputRef = useRef<HTMLInputElement>(null);

  return (
    <div className="relative w-full max-w-2xl mx-auto">
      <input
        ref={inputRef}
        type="text"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder="Search by artist or title..."
        className="w-full rounded-xl border border-neutral-300 bg-white px-4 py-3 pr-11 text-base focus:outline-none focus:ring-2 focus:ring-amber-500 transition-shadow dark:border-neutral-700 dark:bg-neutral-900 sm:px-5 sm:text-lg"
      />
      {value && (
        <button
          onClick={() => {
            onChange("");
            inputRef.current?.focus();
          }}
          className="absolute right-3 top-1/2 -translate-y-1/2 p-1 text-neutral-400 hover:text-neutral-600 dark:hover:text-neutral-200 sm:right-4"
        >
          ✕
        </button>
      )}
    </div>
  );
}
