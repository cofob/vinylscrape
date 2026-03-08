"use client";

import {
  createContext,
  useCallback,
  useContext,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from "react";

export interface PlaylistItem {
  url: string;
  title: string;
}

interface YouTubePlayerContextValue {
  /** Currently playing item, or null when nothing is playing. */
  current: PlaylistItem | null;
  /** Whether there is a previous track available. */
  hasPrev: boolean;
  /** Whether there is a next track available. */
  hasNext: boolean;
  /** Start playing a URL. If it exists in the playlist, playback continues from there. */
  play: (url: string, title: string) => void;
  /** Skip to the previous playlist item that has a different video URL. */
  previous: () => void;
  /** Skip to the next playlist item that has a different video URL. */
  next: () => void;
  /** Stop playback and dismiss the player. */
  close: () => void;
  /** Replace the playlist. Items without a url are silently filtered out. */
  setPlaylist: (items: PlaylistItem[]) => void;
}

const YouTubePlayerContext = createContext<YouTubePlayerContextValue>({
  current: null,
  hasPrev: false,
  hasNext: false,
  play: () => {},
  previous: () => {},
  next: () => {},
  close: () => {},
  setPlaylist: () => {},
});

export function YouTubePlayerProvider({ children }: { children: ReactNode }) {
  const [current, setCurrent] = useState<PlaylistItem | null>(null);
  const playlistRef = useRef<PlaylistItem[]>([]);

  // Index of the currently playing item inside the playlist (-1 = not found / freestanding play).
  const indexRef = useRef(-1);

  const findPrev = useCallback((): PlaylistItem | null => {
    const list = playlistRef.current;
    const idx = indexRef.current;
    if (idx <= 0) return null;
    // Find previous item with a different URL
    for (let i = idx - 1; i >= 0; i--) {
      if (list[i].url !== list[idx]?.url) return list[i];
    }
    return null;
  }, []);

  const findNext = useCallback((): PlaylistItem | null => {
    const list = playlistRef.current;
    const idx = indexRef.current;
    if (idx < 0 || idx >= list.length - 1) return null;
    // Find next item with a different URL
    for (let i = idx + 1; i < list.length; i++) {
      if (list[i].url !== list[idx]?.url) return list[i];
    }
    return null;
  }, []);

  const [hasPrev, setHasPrev] = useState(false);
  const [hasNext, setHasNext] = useState(false);

  const updateNav = useCallback(() => {
    setHasPrev(findPrev() !== null);
    setHasNext(findNext() !== null);
  }, [findPrev, findNext]);

  const play = useCallback(
    (url: string, title: string) => {
      setCurrent({ url, title });
      // Try to find this url in the playlist to anchor the index
      const idx = playlistRef.current.findIndex((p) => p.url === url);
      indexRef.current = idx;
      updateNav();
    },
    [updateNav],
  );

  const jumpTo = useCallback(
    (item: PlaylistItem) => {
      const idx = playlistRef.current.findIndex((p) => p.url === item.url);
      indexRef.current = idx;
      setCurrent(item);
      updateNav();
    },
    [updateNav],
  );

  const previous = useCallback(() => {
    const prevItem = findPrev();
    if (prevItem) jumpTo(prevItem);
  }, [findPrev, jumpTo]);

  const next = useCallback(() => {
    const nextItem = findNext();
    if (nextItem) jumpTo(nextItem);
  }, [findNext, jumpTo]);

  const close = useCallback(() => {
    setCurrent(null);
    indexRef.current = -1;
    setHasPrev(false);
    setHasNext(false);
  }, []);

  const setPlaylist = useCallback(
    (items: PlaylistItem[]) => {
      playlistRef.current = items;
      // Re-anchor current index if something is playing
      if (current) {
        const idx = items.findIndex((p) => p.url === current.url);
        indexRef.current = idx;
      }
      updateNav();
    },
    [current, updateNav],
  );

  const value = useMemo(
    () => ({ current, hasPrev, hasNext, play, previous, next, close, setPlaylist }),
    [current, hasPrev, hasNext, play, previous, next, close, setPlaylist],
  );

  return (
    <YouTubePlayerContext value={value}>
      {children}
    </YouTubePlayerContext>
  );
}

export function useYouTubePlayer() {
  return useContext(YouTubePlayerContext);
}
