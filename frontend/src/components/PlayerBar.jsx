import { usePlayer, fmtTime } from "../player.jsx";

export default function PlayerBar() {
  const { state, stop, seek } = usePlayer();
  if (!state.url) return null;

  const pct =
    state.duration > 0 ? Math.min(100, (state.currentTime / state.duration) * 100) : 0;

  return (
    <div className="player-bar">
      <button className="player-stop" onClick={stop} title="停止">
        {state.playing ? "⏸" : "▶️"}
      </button>
      <div className="player-meta">
        <div className="player-title">
          {state.filename || "原音片段"}
          <span className="player-range">
            {" "}
            {fmtTime(state.start)} → {state.end != null ? fmtTime(state.end) : "结尾"}
          </span>
        </div>
        <div
          className="player-track"
          onClick={(e) => {
            const rect = e.currentTarget.getBoundingClientRect();
            const t = ((e.clientX - rect.left) / rect.width) * state.duration;
            seek(t);
          }}
        >
          <div className="player-fill" style={{ width: `${pct}%` }} />
          {state.duration > 0 && (
            <>
              <span
                className="player-marker start"
                style={{ left: `${(state.start / state.duration) * 100}%` }}
              />
              {state.end != null && (
                <span
                  className="player-marker end"
                  style={{ left: `${(state.end / state.duration) * 100}%` }}
                />
              )}
            </>
          )}
        </div>
      </div>
      <div className="player-time">
        {fmtTime(state.currentTime)} / {fmtTime(state.duration)}
      </div>
    </div>
  );
}
