import { useEffect, useState } from "react";
import { api } from "../api.js";
import QuoteCard from "../components/QuoteCard.jsx";

export default function BrowseView({ onEdit, notify }) {
  const [releases, setReleases] = useState([]);
  const [release, setRelease] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    (async () => {
      try {
        const list = await api.listReleases();
        setReleases(list);
        if (list.length) {
          setRelease(await api.getRelease(list[0].id));
        }
      } catch (e) {
        notify(e.message);
      } finally {
        setLoading(false);
      }
    })();
  }, []);

  const pick = async (id) => {
    try {
      setRelease(await api.getRelease(id));
    } catch (e) {
      notify(e.message);
    }
  };

  if (loading) return <p className="muted">加载中…</p>;

  if (releases.length === 0) {
    return (
      <section>
        <div className="empty-panel">
          <h2>尚未发布编年版本</h2>
          <p className="muted">在「草稿编辑」中整理事件与引文后，到「发布管理」生成第一个不可变编年版本。</p>
          <button className="btn btn-primary" onClick={() => onEdit(null)}>
            去整理草稿
          </button>
        </div>
      </section>
    );
  }

  return (
    <section className="browse-layout">
      <aside className="panel release-list">
        <h2>编年版本</h2>
        <ul>
          {releases.map((r, i) => (
            <li
              key={r.id}
              className={release?.id === r.id ? "active" : ""}
              onClick={() => pick(r.id)}
            >
              <div className="release-seq">第 {r.sequence} 版{i === 0 && <span className="latest-tag">最新</span>}</div>
              <div className="release-label">{r.label}</div>
              <div className="muted small">
                {new Date(r.published_at).toLocaleString("zh-CN")} · {r.event_count} 个事件
              </div>
            </li>
          ))}
        </ul>
        <p className="hint">已发布版本不可修改；后续改稿只会出现在新版本中。</p>
      </aside>

      <div className="chronicle">
        {release && (
          <header className="chronicle-head panel">
            <div>
              <h2>
                《{release.label}》
                <span className="muted small"> 第 {release.sequence} 版 · 不可变快照</span>
              </h2>
              {release.note && <p className="muted">{release.note}</p>}
              <p className="muted small">
                发布时间 {new Date(release.published_at).toLocaleString("zh-CN")}
              </p>
            </div>
            <button className="btn" onClick={() => onEdit(null)}>
              去修订草稿
            </button>
          </header>
        )}

        {release?.events.map((s, i) => (
          <article className="event-timeline panel" key={s.id}>
            <div className="event-dot" />
            <div className="event-body">
              <div className="event-date-line">
                <span className="event-date">{s.event_date}</span>
                <h3 className="event-title">
                  {s.title}
                  {s.location && <span className="event-location"> · {s.location}</span>}
                </h3>
              </div>
              {s.description && <p className="event-desc">{s.description}</p>}
              <div className="quote-parallel">
                {s.quotes.length === 0 && <p className="muted small">（此事件暂无引文）</p>}
                {s.quotes.map((q, qi) => (
                  <QuoteCard key={q.id} quote={q} index={qi} />
                ))}
              </div>
            </div>
          </article>
        ))}
      </div>
    </section>
  );
}
