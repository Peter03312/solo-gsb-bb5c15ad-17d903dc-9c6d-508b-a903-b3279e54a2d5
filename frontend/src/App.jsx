import { useCallback, useState } from "react";
import MediaView from "./views/MediaView.jsx";
import DraftsView from "./views/DraftsView.jsx";
import PublishView from "./views/PublishView.jsx";
import BrowseView from "./views/BrowseView.jsx";
import PlayerBar from "./components/PlayerBar.jsx";

const TABS = [
  { key: "browse", label: "编年浏览", icon: "📜" },
  { key: "drafts", label: "草稿编辑", icon: "✏️" },
  { key: "media", label: "音频库", icon: "🎙️" },
  { key: "publish", label: "发布管理", icon: "📮" },
];

export default function App() {
  const [tab, setTab] = useState("browse");
  const [notice, setNotice] = useState(null);

  const notify = useCallback((message, kind = "error") => {
    setNotice({ message, kind, id: Date.now() });
  }, []);

  const goDraftsEdit = useCallback((eventId) => {
    setTab("drafts");
    window.dispatchEvent(new CustomEvent("open-event", { detail: eventId }));
  }, []);

  return (
    <div className="app-shell">
      <header className="topbar">
        <div className="brand">
          <span className="brand-mark">志</span>
          <div>
            <h1>地方博物馆 · 口述史编年工作台</h1>
            <p>录音 / 逐字稿 / 多说法引文 / 不可变编年版本</p>
          </div>
        </div>
        <nav className="tabs">
          {TABS.map((t) => (
            <button
              key={t.key}
              className={tab === t.key ? "tab active" : "tab"}
              onClick={() => setTab(t.key)}
            >
              <span aria-hidden>{t.icon}</span>
              {t.label}
            </button>
          ))}
        </nav>
      </header>

      <main className="content" style={{ paddingBottom: 96 }}>
        {tab === "browse" && <BrowseView onEdit={goDraftsEdit} notify={notify} />}
        {tab === "drafts" && <DraftsView notify={notify} />}
        {tab === "media" && <MediaView notify={notify} />}
        {tab === "publish" && <PublishView notify={notify} />}
      </main>

      <PlayerBar />

      {notice && (
        <div className={`toast toast-${notice.kind}`} onClick={() => setNotice(null)}>
          <span>{notice.kind === "error" ? "⚠️ " : notice.kind === "success" ? "✅ " : "ℹ️ "}</span>
          <span>{notice.message}</span>
        </div>
      )}
    </div>
  );
}
