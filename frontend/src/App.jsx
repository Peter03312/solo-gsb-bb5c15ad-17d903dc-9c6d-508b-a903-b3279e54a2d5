import { useRef, useState } from 'react'
import AudiosPage from './pages/AudiosPage.jsx'
import EventsPage from './pages/EventsPage.jsx'
import PublishPage from './pages/PublishPage.jsx'
import BrowsePage from './pages/BrowsePage.jsx'
import PlayerBar from './components/PlayerBar.jsx'

const TABS = [
  { key: 'browse', label: '编年浏览' },
  { key: 'events', label: '事件草稿' },
  { key: 'audios', label: '音频库' },
  { key: 'publish', label: '发布' },
]

export default function App() {
  const [tab, setTab] = useState('browse')
  // 跨页面共享的播放目标：{ url, label, startSec }
  const [playTarget, setPlayTarget] = useState(null)
  const playerRef = useRef(null)
  // 发布后跳转到浏览页并定位到指定版本
  const [browseVersionId, setBrowseVersionId] = useState(null)

  const playQuote = (audioId, startSec, label) => {
    setPlayTarget({
      url: `/api/audios/${audioId}/stream`,
      label: label || `音频 #${audioId}`,
      startSec: Number(startSec) || 0,
    })
    // 等 PlayerBar 拿到新 target 后 seek
    requestAnimationFrame(() => playerRef.current?.seekTo(Number(startSec) || 0))
  }

  const gotoBrowseVersion = (pubId) => {
    setBrowseVersionId(pubId)
    setTab('browse')
  }

  return (
    <div className="app">
      <header className="topbar">
        <div className="brand">🏛️ 地方博物馆 · 口述史编年工作台</div>
        <nav className="tabs">
          {TABS.map((t) => (
            <button
              key={t.key}
              className={`tab ${tab === t.key ? 'active' : ''}`}
              onClick={() => setTab(t.key)}
            >
              {t.label}
            </button>
          ))}
        </nav>
      </header>

      <main className="content">
        {tab === 'browse' && (
          <BrowsePage
            onPlay={playQuote}
            versionId={browseVersionId}
            versionConsumed={() => setBrowseVersionId(null)}
          />
        )}
        {tab === 'events' && <EventsPage onPlay={playQuote} />}
        {tab === 'audios' && <AudiosPage />}
        {tab === 'publish' && <PublishPage onPublished={gotoBrowseVersion} />}
      </main>

      {playTarget && (
        <PlayerBar
          ref={playerRef}
          target={playTarget}
          onClose={() => setPlayTarget(null)}
        />
      )}
    </div>
  )
}
