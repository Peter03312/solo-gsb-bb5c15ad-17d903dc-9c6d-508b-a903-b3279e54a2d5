import { useEffect, useState } from "react";
import { api } from "../api.js";

export default function PublishView({ notify }) {
  const [releases, setReleases] = useState([]);
  const [drafts, setDrafts] = useState([]);
  const [label, setLabel] = useState("");
  const [note, setNote] = useState("");
  const [publishing, setPublishing] = useState(false);

  const refresh = async () => {
    const [rs, es] = await Promise.all([api.listReleases(), api.listEvents()]);
    setReleases(rs);
    setDrafts(es);
  };

  useEffect(() => {
    refresh().catch((e) => notify(e.message));
  }, []);

  const publish = async () => {
    if (!label.trim()) {
      notify("请填写版本名称");
      return;
    }
    if (drafts.length === 0) {
      notify("没有草稿可发布");
      return;
    }
    const nextSeq = (releases[0]?.sequence || 0) + 1;
    if (!window.confirm(`将把当前 ${drafts.length} 个事件草稿固化为「第 ${nextSeq} 版」。\n发布后该版本内容不可更改，确认继续？`))
      return;
    setPublishing(true);
    try {
      const r = await api.publishRelease({ label: label.trim(), note });
      notify(`已发布第 ${r.sequence} 版：${r.label}`, "success");
      setLabel("");
      setNote("");
      await refresh();
    } catch (e) {
      notify(e.body?.detail || e.message);
    } finally {
      setPublishing(false);
    }
  };

  return (
    <section className="publish-layout">
      <div className="panel">
        <h2>生成新的编年版本</h2>
        <p className="muted">
          发布操作会把<b>当前所有事件草稿及其引文</b>深拷贝为一份不可变快照：
          此后即便草稿被修订、引文起止秒被调整，旧版本中读者看到的引文文字与跳转的原音片段都保持不变。
        </p>
        <div className="form-grid">
          <label className="span-2">
            版本名称 *
            <input
              value={label}
              onChange={(e) => setLabel(e.target.value)}
              placeholder={`如：2026 年秋季编订（第 ${(releases[0]?.sequence || 0) + 1} 版）`}
              maxLength={256}
            />
          </label>
          <label className="span-2">
            版本说明
            <textarea rows={3} value={note} onChange={(e) => setNote(e.target.value)} placeholder="本次新增/订正了哪些内容…" />
          </label>
        </div>
        <div className="editor-actions">
          <button className="btn btn-primary" disabled={publishing || !drafts.length} onClick={publish}>
            {publishing ? "发布中…" : `发布第 ${(releases[0]?.sequence || 0) + 1} 版`}
          </button>
          <span className="muted small">将纳入 {drafts.length} 个事件草稿</span>
        </div>
      </div>

      <div className="panel">
        <h2>已发布版本（{releases.length}）</h2>
        {releases.length === 0 ? (
          <p className="empty">还没有发布过版本。</p>
        ) : (
          <table className="release-table">
            <thead>
              <tr>
                <th>版本</th>
                <th>名称</th>
                <th>事件数</th>
                <th>发布时间</th>
              </tr>
            </thead>
            <tbody>
              {releases.map((r) => (
                <tr key={r.id}>
                  <td>第 {r.sequence} 版</td>
                  <td>{r.label}{r.note && <div className="muted small">{r.note}</div>}</td>
                  <td>{r.event_count}</td>
                  <td>{new Date(r.published_at).toLocaleString("zh-CN")}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </section>
  );
}
