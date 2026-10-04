import { usePlayer, fmtTime } from "../player.jsx";

// A quote card showing the transcribed text and a button that jumps to the
// original audio at its start second.
export default function QuoteCard({ quote, index }) {
  const { playClip, isClipPlaying } = usePlayer();
  const clip = {
    url: quote.audio_url,
    filename: quote.media_filename,
    start: quote.start_sec,
    end: quote.end_sec,
  };
  const playing = isClipPlaying(clip);

  return (
    <figure className={`quote-card ${playing ? "playing" : ""}`}>
      <figcaption className="quote-head">
        <span className="quote-index">说法 {index + 1}</span>
        {quote.speaker && <span className="quote-speaker">讲述人：{quote.speaker}</span>}
        <span className="quote-time">
          {fmtTime(quote.start_sec)} – {fmtTime(quote.end_sec)}
        </span>
        <button
          type="button"
          className={`btn btn-audio ${playing ? "on" : ""}`}
          onClick={() => playClip(clip)}
          title="跳至原音播放此引文"
        >
          {playing ? "⏸ 暂停原音" : "▶ 听原音"}
        </button>
      </figcaption>
      <blockquote className="quote-text">{quote.text || "（未填写引文文字）"}</blockquote>
      <div className="quote-source">🎙 {quote.media_filename}</div>
    </figure>
  );
}
