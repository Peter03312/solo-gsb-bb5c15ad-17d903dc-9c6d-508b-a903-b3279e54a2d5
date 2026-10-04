import { useEffect, useState } from 'react'
import { api } from '../api.js'
import EventEditor from '../components/EventEditor.jsx'

// 事件草稿列表 + 新建/编辑/删除
export default function EventsPage({ onPlay }) {
  const [events, setEvents] = useState([])
  const [audios, setAudios] = useState([])
  const [editingId, setEditingId] = useState(null) // null=列表, 'new'=新建, number=编辑
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  const load = async () => {
    setLoading(true)
    setError('')
    try {
      const [evs, aus] = await Promise.all([api.listEvents(), api.listAudios()])
      setEvents(evs)
      setAudios(aus)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { load() }, [])

  const handleSaved = () => {
    setEditingId(null)
    load()
  }

  const handleDelete = async (ev) => {
    if (!window.confirm(`确定删除草稿事件「${ev.title}」？此操作仅影响草稿，已发布版本不受影响。`)) return
    try {
      await api.deleteEvent(ev.id)
      load()
    } catch (err) {
      window.alert(err.message)
    }
  }

  if (loading) return <div className="empty">加载中…</div>

  if (editingId !== null) {
    const event = editingId === 'new' ? null : events.find((e) => e.id === editingId)
    if (editingId !== 'new' && !event) {
      // 事件可能在其他窗口被删除，拉取最新
      return <div className="empty">事件不存在或已被删除。<button className="btn-link" onClick={load}>返回列表</button></div>
    }
    return (
      <div>
        <h2>{editingId === 'new' ? '新建事件' : `编辑事件 · v${event.revision}`}</h2>
        <EventEditor
          event={event}
          audios={audios}
          onPlay={onPlay}
          onSaved={handleSaved}
          onCancel={() => setEditingId(null)}
        />
      </div>
    )
  }

  return (
    <div>
      <div className="page-head">
        <h2>事件草稿（{events.length}）</h2>
        <button className="btn btn-primary" onClick={() => setEditingId('new')}>
          ＋ 新建事件
        </button>
      </div>
      {error && <div className="alert alert-error">{error}</div>}
      {events.length === 0 ? (
        <div className="empty">还没有事件草稿，点击右上角「新建事件」开始整理。</div>
      ) : (
        <div className="event-list">
          {events.map((ev) => (
            <div key={ev.id} className="event-item">
              <div className="event-item-main">
                <div className="event-date">{ev.event_date}</div>
                <div className="event-title">{ev.title}</div>
                <div className="event-meta">
                  {ev.quotes.length} 条引文
                  {ev.quotes.length > 1 && '（多种说法）'} · 修订 v{ev.revision}
                </div>
              </div>
              <div className="event-item-actions">
                <button className="btn btn-small" onClick={() => setEditingId(ev.id)}>
                  编辑
                </button>
                <button className="btn btn-small btn-danger-outline" onClick={() => handleDelete(ev)}>
                  删除
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
