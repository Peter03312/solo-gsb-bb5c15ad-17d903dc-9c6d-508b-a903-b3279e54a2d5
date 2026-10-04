import { createContext, useCallback, useContext, useRef, useState } from "react";

const PlayerContext = createContext(null);

export function PlayerProvider({ children }) {
  const audioRef = useRef(null);
  const [state, setState] = useState({
    url: null,
    filename: "",
    start: 0,
    end: null, // null = play to the end of the file
    playing: false,
    currentTime: 0,
    duration: 0,
  });

  const stopAtEndRef = useRef(null);

  const ensureAudio = useCallback(() => {
    if (!audioRef.current) {
      const el = new Audio();
      el.preload = "metadata";

      el.addEventListener("timeupdate", () => {
        const stopAt = stopAtEndRef.current;
        if (stopAt != null && el.currentTime >= stopAt) {
          el.pause();
          el.currentTime = stopAt;
          setState((s) => ({ ...s, playing: false, currentTime: stopAt }));
          return;
        }
        setState((s) => ({ ...s, currentTime: el.currentTime }));
      });
      el.addEventListener("loadedmetadata", () =>
        setState((s) => ({ ...s, duration: el.duration || 0 }))
      );
      el.addEventListener("play", () => setState((s) => ({ ...s, playing: true })));
      el.addEventListener("pause", () => setState((s) => ({ ...s, playing: false })));
      el.addEventListener("ended", () =>
        setState((s) => ({ ...s, playing: false, currentTime: 0 }))
      );
      audioRef.current = el;
    }
    return audioRef.current;
  }, []);

  // Play a clip. Same clip toggles play/pause; a new clip seeks to start.
  const playClip = useCallback(
    ({ url, filename, start, end }) => {
      const el = ensureAudio();
      const sameClip =
        state.url === url && state.start === start &&
        (state.end ?? null) === (end ?? null);

      if (sameClip) {
        if (el.paused) el.play();
        else el.pause();
        return;
      }

      const absoluteUrl = new URL(url, window.location.origin).href;
      if (clipUrlRef.current !== absoluteUrl) {
        el.src = absoluteUrl;
        clipUrlRef.current = absoluteUrl;
      }
      stopAtEndRef.current = end ?? null;
      el.currentTime = start;
      setState((s) => ({
        ...s,
        url,
        filename: filename || "",
        start,
        end: end ?? null,
        currentTime: start,
      }));
      el.play().catch(() => {});
    },
    [ensureAudio, state.url, state.start, state.end]
  );

  const stop = useCallback(() => {
    const el = audioRef.current;
    if (el) {
      el.pause();
      setState((s) => ({ ...s, playing: false }));
    }
  }, []);

  const seek = useCallback((sec) => {
    const el = audioRef.current;
    if (el) {
      el.currentTime = sec;
      setState((s) => ({ ...s, currentTime: sec }));
    }
  }, []);

  const isClipPlaying = useCallback(
    ({ url, start, end }) =>
      state.playing &&
      state.url === url &&
      state.start === start &&
      (state.end ?? null) === (end ?? null),
    [state]
  );

  return (
    <PlayerContext.Provider value={{ state, playClip, stop, seek, isClipPlaying }}>
      {children}
    </PlayerContext.Provider>
  );
}

export function usePlayer() {
  const ctx = useContext(PlayerContext);
  if (!ctx) throw new Error("usePlayer must be used within PlayerProvider");
  return ctx;
}

export function fmtTime(sec) {
  if (sec == null || Number.isNaN(sec)) return "--:--";
  sec = Math.max(0, sec);
  const h = Math.floor(sec / 3600);
  const m = Math.floor((sec % 3600) / 60);
  const s = Math.floor(sec % 60);
  const ms = Math.floor((sec % 1) * 10);
  if (h > 0)
    return `${h}:${String(m).padStart(2, "0")}:${String(s).padStart(2, "0")}.${ms}`;
  return `${String(m).padStart(2, "0")}:${String(s).padStart(2, "0")}.${ms}`;
}
