"use client";

import { useState } from "react";
import { useYouTubePlayer } from "@/lib/youtube-player";

function extractVideoId(url: string): string | null {
  const patterns = [
    /(?:youtube\.com\/watch\?v=)([a-zA-Z0-9_-]{11})/,
    /(?:youtu\.be\/)([a-zA-Z0-9_-]{11})/,
    /(?:youtube\.com\/embed\/)([a-zA-Z0-9_-]{11})/,
  ];

  for (const pattern of patterns) {
    const match = url.match(pattern);
    if (match) return match[1];
  }
  return null;
}

export default function YouTubePlayerPopup() {
  const { current, hasPrev, hasNext, previous, next, close } = useYouTubePlayer();
  const [collapsed, setCollapsed] = useState(true);

  if (!current) return null;

  const videoId = extractVideoId(current.url);
  if (!videoId) return null;

  return (
    <div
      className={`fixed z-50 bg-black shadow-2xl
        inset-x-0 bottom-0 sm:inset-x-auto sm:bottom-4 sm:right-4 sm:w-96 sm:rounded-xl sm:overflow-hidden`}
    >
      {/* Header with title, collapse toggle, next, and close buttons */}
      <div className="flex items-center justify-between px-3 py-2 bg-neutral-900">
        <button
          onClick={() => setCollapsed((c) => !c)}
          className="flex items-center gap-2 min-w-0 mr-2 sm:pointer-events-none"
          aria-label={collapsed ? "Expand player" : "Collapse player"}
        >
          {/* Chevron — only visible on mobile */}
          <svg
            xmlns="http://www.w3.org/2000/svg"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth={2}
            strokeLinecap="round"
            strokeLinejoin="round"
            className={`w-4 h-4 shrink-0 text-neutral-400 transition-transform sm:hidden ${
              collapsed ? "rotate-180" : ""
            }`}
          >
            <path d="m6 9 6 6 6-6" />
          </svg>
          <p className="text-white text-xs truncate">{current.title}</p>
        </button>
        <div className="flex items-center gap-1 shrink-0">
          {/* Previous button */}
          {hasPrev && (
            <button
              onClick={previous}
              className="p-1 rounded-lg text-neutral-400 hover:text-white hover:bg-neutral-700 transition-colors"
              aria-label="Previous"
              title="Previous"
            >
              <svg
                xmlns="http://www.w3.org/2000/svg"
                viewBox="0 0 24 24"
                fill="currentColor"
                className="w-4 h-4"
              >
                <rect x="5" y="4" width="2" height="16" />
                <path d="M18 4L8 12l10 8V4z" />
              </svg>
            </button>
          )}
          {/* Next button */}
          {hasNext && (
            <button
              onClick={next}
              className="p-1 rounded-lg text-neutral-400 hover:text-white hover:bg-neutral-700 transition-colors"
              aria-label="Next"
              title="Next"
            >
              <svg
                xmlns="http://www.w3.org/2000/svg"
                viewBox="0 0 24 24"
                fill="currentColor"
                className="w-4 h-4"
              >
                <path d="M6 4l10 8-10 8V4z" />
                <rect x="17" y="4" width="2" height="16" />
              </svg>
            </button>
          )}
          {/* Close button */}
          <button
            onClick={close}
            className="p-1 rounded-lg text-neutral-400 hover:text-white hover:bg-neutral-700 transition-colors"
            aria-label="Close player"
          >
            <svg
              xmlns="http://www.w3.org/2000/svg"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth={2}
              strokeLinecap="round"
              strokeLinejoin="round"
              className="w-4 h-4"
            >
              <path d="M18 6 6 18" />
              <path d="M6 6l12 12" />
            </svg>
          </button>
        </div>
      </div>
      {/* YouTube iframe — collapsed on mobile by default, always visible on sm+ */}
      <div
        className={`relative aspect-video transition-[max-height] duration-300 overflow-hidden
          ${collapsed ? "max-h-0" : "max-h-[56.25vw]"} sm:max-h-none`}
      >
        <iframe
          src={`https://www.youtube-nocookie.com/embed/${videoId}?autoplay=1`}
          title="YouTube video player"
          allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
          allowFullScreen
          className="absolute inset-0 w-full h-full"
        />
      </div>
    </div>
  );
}
