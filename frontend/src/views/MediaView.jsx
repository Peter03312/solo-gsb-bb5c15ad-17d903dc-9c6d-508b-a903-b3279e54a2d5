import { useEffect, useRef, useState } from "react";
import { api, ApiError } from "../api.js";
import { fmtTime } from "../player.jsx";

export default function MediaView({ notify }) {
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [progress, setProgress] = useState("");
  const audioInput = useRef(null);

  const refresh = async () => {
    try {
      setItems(await api.listMedia());
    } catch (e) {
      notify(e.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    refresh();
  }, []);

  const onUpload = async () => {
    const file = audioInput.current?.files?.[0];
    if (!file) {
      notify("请先选择 MP3 或 WAV 音频文件");
      return;
    }
    const ext = file.name.toLowerCase().split(".").pop();
    if (!["mp3", "wav"].includes(ext)) {
      notify("音频仅支持 .mp3 / .wav");
      return;
    }
    const fd = new FormData();
    fd.append("audio", file);
    if (transcriptInput.current?.files?.[0]) {
      fd.append("transcript", transcriptInput.current.files[0]);
    }
    fd.append("speaker", speakerRef.current?.value?.trim() || "");

    setUploading(true);
    setProgress("正在上传并校验音频（失败不会留下半成品）…");
    try {
      const created = await api.uploadMedia(fd);
      notify(`已入库：${created.original_filename}（时长 ${fmtTime(created.duration_seconds)}）`, "success");
      if (audioInput.current) audioInput.current.value = "";
      if (transcriptInput.current) transcriptInput.current.value = "";
      if (speakerRef.current) speakerRef.current.value = "";
      await refresh();
    } catch (e) {
      notify(e.body?.detail || "上传失败，请重试");
    } finally {
      setUploading(false);
      setProgress("");
    }
  };

  const transcriptInput = useRef(null);
  const speakerRef = useRef(null);

  const onDelete = async (m) => {
    if (!window.confirm(`确认删除音频《${m.original_filename}》？\n若已被引用将被拒绝。`)) return;
    try {
      await api.deleteMedia(m.id);
      notify("已删除", "success");
      await refresh();
    } catch (e) {
      notify(e.body?.detail || "删除失败");
    }
  };

  return (
    <section>
      <div className="panel">
        <h2>上传口述原音与逐字稿</h2>
        <p className="muted">
          支持 <b>.mp3 / .wav</b> 音频，逐字稿支持 <b>.txt / .srt / .vtt</b>（UTF-8 编码）。
          上传后服务器会校验音频可读取、时长有效、逐字稿可解析；任一步失败都不会产生记录或残留文件。
        </p>
        <div className="upload-grid">
          <label>
            音频文件 *
            <input ref={audioInput} type="file" accept=".mp3,.wav,audio/mpeg,audio/wav" />
          </label>
          <label>
            逐字稿（可选）
            <input ref={transcriptInput} type="file" accept=".txt,.srt,.vtt" />
          </label>
          <label>
            讲述人 / 受访者
            <input ref={speakerRef} type="text" placeholder="如：王阿婆（1931— ）" maxLength={256} />
          </label>
          <div className="upload-action">
            <button className="btn btn-primary" disabled={uploading} onClick={onUpload}>
              {uploading ? "上传中…" : "上传入库"}
            </button>
            {progress && <span className="hint">{progress}</span>}
          </div>
        </div>
      </div>

      <h2 className="section-title">音频库（{items.length}）</h2>
      {loading ? (
        <p className="muted">加载中…</p>
      ) : items.length === 0 ? (
        <p className="empty">还没有音频。先在上方上传一段采访录音吧。</p>
      ) : (
        <div className="media-grid">
          {items.map((m) => (
            <div className="media-card" key={m.id}>
              <div className="media-card-head">
                <span className="media-icon">🎙</span>
                <div>
                  <div className="media-name" title={m.original_filename}>
                    {m.original_filename}
                  </div>
                  <div className="muted small">
                    {fmtTime(m.duration_seconds)}
                    {m.speaker ? ` · ${m.speaker}` : ""}
                  </div>
                </div>
              </div>
              <audio controls preload="none" src={m.audio_url} style={{ width: "100%" }} />
              <div className="media-card-foot">
                {m.transcript_url ? (
                  <a className="btn btn-small" href={m.transcript_url} target="_blank" rel="noreferrer">
                    查看逐字稿（{m.transcript_kind}）
                  </a>
                ) : (
                  <span className="muted small">无逐字稿</span>
                )}
                <button className="btn btn-danger btn-small" onClick={() => onDelete(m)}>
                  删除
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </section>
  );
}
