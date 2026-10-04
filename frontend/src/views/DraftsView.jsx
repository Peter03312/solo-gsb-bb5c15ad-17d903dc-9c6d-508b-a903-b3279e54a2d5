import { useEffect, useMemo, useState } from "react";
import { api } from "../api.js";
import { usePlayer, fmtTime } from "../player.jsx";
import QuoteCard from "../components/QuoteCard.jsx";
import ConflictDialog from "../components/ConflictDialog.jsx";

const EMPTY_FORM = {
  id: null,
  title: "",
  event_date: "",
  location: "",
  description: "",
  revision: null,
  quotes: [],
};

export default function DraftsView({ notify }) {
  const [events, setEvents] = useState([]);
  const [media, setMedia] = useState([]);
  const [form, setForm] = useState(EMPTY_FORM);
  const [selectedId, setSelectedId] = useState(null);
  const [saving, setSaving] = useState(false);
  const [conflict, setConflict] = useState(null);
  const { state } = usePlayer();

  const refresh = async () => {
    const [es, ms] = await Promise.all([api.listEvents(), api.listMedia()]);
    setEvents(es);
    setMedia(ms);
    return es;
  };

  useEffect(() => {
    refresh().catch((e) => notify(e.message));
  }, []);

  // external request to open an event (from BrowseView "去修订" button)
  useEffect(() => {
    const handler = (e) => {
      const id = e.detail;
      if (id) selectEvent(id);
      else newEvent();
    };
    window.addEventListener("open-event", handler);
    return () => window.removeEventListener("open-event", handler);
  }, [events]);

  const selectEvent = async (id) => {
    try {
      const e = await api.getEvent(id);
      setForm({
        id: e.id,
        title: e.title,
        event_date: e.event_date,
        location: e.location,
        description: e.description,
        revision: e.revision,
        quotes: e.quotes.map((q) => ({
          media_id: q.media_id,
          speaker: q.speaker || "",
          start_sec: q.start_sec,
          end_sec: q.end_sec,
          text: q.text,
        })),
      });
      setSelectedId(id);
    } catch (e) {
      notify(e.message);
    }
  };

  const newEvent = () => {
    setForm(EMPTY_FORM);
    setSelectedId(null);
  };

  const patch = (key, value) => setForm((f) => ({ ...f, [key]: value }));

  const patchQuote = (idx, key, value) =>
    setForm((f) => ({
      ...f,
      quotes: f.quotes.map((q, i) => (i === idx ? { ...q, [key]: value } : q)),
    }));

  const addQuote = () => {
    const first = media[0];
    setForm((f) => ({
      ...f,
      quotes: [
        ...f.quotes,
        {
          media_id: first?.id ?? 0,
          speaker: first?.speaker || "",
          start_sec: 0,
          end_sec: first ? Math.min(5, first.duration_seconds) : 1,
          text: "",
        },
      ],
    }));
  };

  const removeQuote = (idx) =>
    setForm((f) => ({ ...f, quotes: f.quotes.filter((_, i) => i !== idx) }));

  const moveQuote = (idx, dir) => {
    const j = idx + dir;
    if (j < 0 || j >= form.quotes.length) return;
    const next = [...form.quotes];
    [next[idx], next[j]] = [next[j], next[idx]];
    setForm((f) => ({ ...f, quotes: next }));
  };

  // local client-side validation mirrors the server rules for instant hints
  const errors = useMemo(() => {
    const errs = [];
    if (!form.title.trim()) errs.push("标题不能为空");
    if (!/^\d{4}(-\d{2}(-\d{2})?)?$/.test(form.event_date))
      errs.push("事件日期应为 YYYY、YYYY-MM 或 YYYY-MM-DD");
    form.quotes.forEach((q, i) => {
      const m = media.find((x) => x.id === Number(q.media_id));
      if (!m) errs.push(`第 ${i + 1} 条引文：请选择音频`);
      else {
        if (!(q.end_sec > q.start_sec)) errs.push(`第 ${i + 1} 条引文：结束秒必须大于开始秒`);
        else if (q.end_sec - q.start_sec < 0.1) errs.push(`第 ${i + 1} 条引文：时长不足 0.1 秒`);
        if (q.start_sec < 0) errs.push(`第 ${i + 1} 条引文：开始秒不能为负`);
        if (q.end_sec > m.duration_seconds + 0.05)
          errs.push(`第 ${i + 1} 条引文：超出音频时长 ${fmtTime(m.duration_seconds)}`);
      }
    });
    return errs;
  }, [form, media]);

  const save = async () => {
    if (errors.length) {
      notify(errors[0]);
      return;
    }
    const payload = {
      title: form.title.trim(),
      event_date: form.event_date,
      location: form.location,
      description: form.description,
      quotes: form.quotes.map((q) => ({
        media_id: Number(q.media_id),
        speaker: q.speaker?.trim() || null,
        start_sec: Number(q.start_sec),
        end_sec: Number(q.end_sec),
        text: q.text,
      })),
    };
    setSaving(true);
    try {
      let saved;
      if (form.id) {
        saved = await api.updateEvent(form.id, { ...payload, revision: form.revision });
      } else {
        saved = await api.createEvent(payload);
      }
      notify(form.id ? `已保存（修订 #${saved.revision}）` : "草稿已创建", "success");
      const es = await refresh();
      await selectEvent(saved.id);
    } catch (e) {
      if (e.status === 409 && e.body?.server_event) {
        setConflict(e.body);
      } else {
        notify(e.body?.detail || e.message);
      }
    } finally {
      setSaving(false);
    }
  };

  const removeEvent = async () => {
    if (!form.id) return;
    if (!window.confirm("删除此事件草稿？已发布编年版本中的快照不受影响，但草稿将不可恢复。")) return;
    try {
      await api.deleteEvent(form.id);
      notify("草稿已删除", "success");
      newEvent();
      await refresh();
    } catch (e) {
      notify(e.body?.detail || e.message);
    }
  };

  const resolveConflict = ({ base, server }) => {
    if (base === "server") {
      setForm({
        id: server.id,
        title: server.title,
        event_date: server.event_date,
        location: server.location,
        description: server.description,
        revision: server.revision,
        quotes: server.quotes.map((q) => ({
          media_id: q.media_id,
          speaker: q.speaker || "",
          start_sec: q.start_sec,
          end_sec: q.end_sec,
          text: q.text,
        })),
      });
    } else {
      // keep the user's edits but rebase onto the newest revision number
      setForm((f) => ({ ...f, id: server.id, revision: server.revision }));
    }
    setConflict(null);
    notify("已按最新修订号对齐，确认内容后再次点击保存即可", "success");
  };

  const usePlayerTime = (idx, which) => {
    if (!state.url) {
      notify("请先在音频库或引文中播放一段原音");
      return;
    }
    const t = Math.round(state.currentTime * 100) / 100;
    patchQuote(idx, which, t);
  };

  const fetchTranscriptText = async (idx) => {
    const q = form.quotes[idx];
    const m = media.find((x) => x.id === Number(q.media_id));
    if (!m) {
      notify("请先选择音频");
      return;
    }
    if (!m.transcript_url) {
      notify("该音频没有 SRT/VTT 逐字稿，无法自动取文");
      return;
    }
    try {
      const r = await api.quoteText(m.id, Number(q.start_sec), Number(q.end_sec));
      patchQuote(idx, "text", r.text || q.text);
      if (!r.text) notify("该时间段内没有匹配的字幕条目");
    } catch (e) {
      notify(e.body?.detail || e.message);
    }
  };

  return (
    <section className="drafts-layout">
      <aside className="draft-list panel">
        <div className="draft-list-head">
          <h2>事件草稿</h2>
          <button className="btn btn-primary btn-small" onClick={newEvent}>
            ＋ 新建
          </button>
        </div>
        {events.length === 0 && <p className="empty">暂无草稿</p>}
        <ul>
          {events.map((e) => (
            <li
              key={e.id}
              className={selectedId === e.id ? "active" : ""}
              onClick={() => selectEvent(e.id)}
            >
              <div className="draft-date">{e.event_date}</div>
              <div className="draft-title">{e.title}</div>
              <div className="draft-meta">
                {e.quotes.length} 条引文 · 修订 #{e.revision}
              </div>
            </li>
          ))}
        </ul>
      </aside>

      <div className="panel editor">
        <div className="editor-head">
          <h2>{form.id ? `编辑事件 #${form.id}` : "新建事件"}</h2>
          {form.id && <span className="rev-tag">当前修订 #{form.revision}</span>}
        </div>

        {media.length === 0 && (
          <div className="warn-box">音频库为空：可先填写事件信息保存，但添加引文前请先到「音频库」上传录音。</div>
        )}

        <div className="form-grid">
          <label className="span-2">
            事件标题 *
            <input value={form.title} onChange={(e) => patch("title", e.target.value)} maxLength={512} />
          </label>
          <label>
            事件日期 *
            <input
              value={form.event_date}
              onChange={(e) => patch("event_date", e.target.value)}
              placeholder="1958 / 1958-12 / 1958-12-20"
            />
          </label>
          <label>
            地点
            <input value={form.location} onChange={(e) => patch("location", e.target.value)} maxLength={256} />
          </label>
          <label className="span-2">
            事件背景说明
            <textarea
              rows={3}
              value={form.description}
              onChange={(e) => patch("description", e.target.value)}
            />
          </label>
        </div>

        <div className="quote-editor-head">
          <h3>并置说法（{form.quotes.length}）</h3>
          <button className="btn btn-small" onClick={addQuote} disabled={!media.length}>
            ＋ 添加引文
          </button>
        </div>
        <p className="muted small">
          同一事件的多种说法在此并列保存；每条引文以音频起止秒锚定，读者在浏览页点击即可跳至原音。
        </p>

        {form.quotes.map((q, idx) => {
          const m = media.find((x) => x.id === Number(q.media_id));
          return (
            <div className="quote-edit" key={idx}>
              <div className="quote-edit-top">
                <strong>说法 {idx + 1}</strong>
                <span className="muted small">
                  {m ? `音频时长 ${fmtTime(m.duration_seconds)}` : "未选择音频"}
                </span>
                <span className="spacer" />
                <button type="button" className="link-btn" onClick={() => moveQuote(idx, -1)}>↑</button>
                <button type="button" className="link-btn" onClick={() => moveQuote(idx, 1)}>↓</button>
                <button type="button" className="link-btn danger" onClick={() => removeQuote(idx)}>
                  删除
                </button>
              </div>
              <div className="quote-edit-grid">
                <label>
                  音频 *
                  <select
                    value={q.media_id}
                    onChange={(e) => {
                      const picked = media.find((x) => x.id === Number(e.target.value));
                      patchQuote(idx, "media_id", e.target.value);
                      if (picked && !q.speaker) patchQuote(idx, "speaker", picked.speaker || "");
                    }}
                  >
                    <option value={0}>— 请选择 —</option>
                    {media.map((x) => (
                      <option key={x.id} value={x.id}>
                        {x.original_filename}（{fmtTime(x.duration_seconds)}）
                      </option>
                    ))}
                  </select>
                </label>
                <label>
                  讲述人（可覆盖）
                  <input
                    value={q.speaker || ""}
                    onChange={(e) => patchQuote(idx, "speaker", e.target.value)}
                    maxLength={256}
                  />
                </label>
                <label>
                  开始秒 *
                  <div className="num-row">
                    <input
                      type="number"
                      min="0"
                      step="0.1"
                      value={q.start_sec}
                      onChange={(e) => patchQuote(idx, "start_sec", e.target.value)}
                    />
                    <button type="button" className="btn btn-small" onClick={() => usePlayerTime(idx, "start_sec")}>
                      取当前播放点
                    </button>
                  </div>
                </label>
                <label>
                  结束秒 *
                  <div className="num-row">
                    <input
                      type="number"
                      min="0"
                      step="0.1"
                      value={q.end_sec}
                      onChange={(e) => patchQuote(idx, "end_sec", e.target.value)}
                    />
                    <button type="button" className="btn btn-small" onClick={() => usePlayerTime(idx, "end_sec")}>
                      取当前播放点
                    </button>
                  </div>
                </label>
                <label className="span-2">
                  引文文字
                  <div className="text-row">
                    <textarea
                      rows={2}
                      value={q.text}
                      onChange={(e) => patchQuote(idx, "text", e.target.value)}
                      placeholder="该时间段受访者原话；可从 SRT/VTT 逐字稿自动截取"
                    />
                    <button type="button" className="btn btn-small" onClick={() => fetchTranscriptText(idx)}>
                      从逐字稿取文
                    </button>
                  </div>
                </label>
              </div>
            </div>
          );
        })}

        {errors.length > 0 && (
          <ul className="error-list">
            {errors.map((x, i) => (
              <li key={i}>{x}</li>
            ))}
          </ul>
        )}

        <div className="editor-actions">
          <button className="btn btn-primary" disabled={saving} onClick={save}>
            {saving ? "保存中…" : form.id ? `保存修订（#${(form.revision || 0) + 1}）` : "创建草稿"}
          </button>
          {form.id && (
            <button className="btn btn-danger" onClick={removeEvent}>
              删除草稿
            </button>
          )}
          <button className="btn" onClick={newEvent}>
            清空 / 新建
          </button>
        </div>
      </div>

      {conflict && (
        <ConflictDialog
          conflict={conflict}
          onChoose={resolveConflict}
          onCancel={() => setConflict(null)}
        />
      )}
    </section>
  );
}
