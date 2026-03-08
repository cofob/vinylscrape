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
  /** Whether there is a next track available. */
  hasNext: boolean;
  /** Start playing a URL. If it exists in the playlist, playback continues from there. */
  play: (url: string, title: string) => void;
  /** Skip to the next playlist item that has a different video URL. */
  next: () => void;
  /** Stop playback and dismiss the player. */
  close: () => void;
  /** Replace the playlist. Items without a url are silently filtered out. */
  setPlaylist: (items: PlaylistItem[]) => void;
}

const YouTubePlayerContext = createContext<YouTubePlayerContextValue>({
  current: null,
  hasNext: false,
  play: () => {},
  next: () => {},
  close: () => {},
  setPlaylist: () => {},
});

export function YouTubePlayerProvider({ children }: { children: ReactNode }) {
  const [current, setCurrent] = useState<PlaylistItem | null>(null);
  const playlistRef = useRef<PlaylistItem[]>([]);

  // Index of the currently playing item inside the playlist (-1 = not found / freestanding play).
  const indexRef = useRef(-1);

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

  const [hasNext, setHasNext] = useState(false);

  const updateHasNext = useCallback(() => {
    setHasNext(findNext() !== null);
  }, [findNext]);

  const play = useCallback(
    (url: string, title: string) => {
      const item = { url, title };
      setCurrent(item);
      // Try to find this url in the playlist to anchor the index
      const idx = playlistRef.current.findIndex((p) => p.url === url);
      indexRef.current = idx;
      updateHasNext();
    },
    [updateHasNext],
  );

  const next = useCallback(() => {
    const nextItem = findNext();
    if (nextItem) {
      const idx = playlistRef.current.findIndex(
        (p) => p.url === nextItem.url,
      );
      indexRef.current = idx;
      setCurrent(nextItem);
      setHasNext(
        (() => {
          const list = playlistRef.current;
          if (idx < 0 || idx >= list.length - 1) return false;
          for (let i = idx + 1; i < list.length; i++) {
            if (list[i].url !== list[idx]?.url) return true;
          }
          return false;
        })(),
      );
    }
  }, [findNext]);

  const close = useCallback(() => {
    setCurrent(null);
    indexRef.current = -1;
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
      updateHasNext();
    },
    [current, updateHasNext],
  );

  const value = useMemo(
    () => ({ current, hasNext, play, next, close, setPlaylist }),
    [current, hasNext, play, next, close, setPlaylist],
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
