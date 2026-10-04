import { useEffect, useState } from 'react'
import { api, formatDateTime } from '../api.js'

// 发布：把当前全部草稿快照为不可变编年版本
export default function PublishPage({ onPublished }) {
  const [events, setEvents] = useState([])
  const [pubs, setPubs] = useState([])
  const [note, setNote] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')

  const load = async () => {
    try {
      const [evs, list] = await Promise.all([api.listEvents(), api.listPublications()])
      setEvents(evs)
      setPubs(list)
    } catch (err) {
      setError(err.message)
    }
  }

  useEffect(() => { load() }, [])

  const handlePublish = async () => {
    if (events.length === 0) return
    if (!window.confirm(
      `将把当前 ${events.length} 个事件快照发布为新版本。发布后内容不可修改，确定继续？`
    )) return
    setBusy(true)
    setError('')
    try {
      const pub = await api.publish({ note })
      setNote('')
      await load()
      onPublished?.(pub.id)
    } catch (err) {
      setError(err.message)
    } finally {
      setBusy(false)
    }
  }

  return (
    <div>
      <h2>发布编年版本</h2>
      <div className="publish-panel">
        <p className="muted">
          发布会把当前所有事件草稿与引文原样固化为一个<strong>不可变版本</strong>。
          之后继续修订草稿不会改变任何已发布版本中的引文；被引用的音频也将受到删除保护。
        </p>
        <div className="form-row">
          <label>版本备注（可选）</label>
          <input
            type="text"
            value={note}
            maxLength={500}
            onChange={(e) => setNote(e.target.value)}
            placeholder="例如：国庆特展前校订版"
          />
        </div>
        {error && <div className="alert alert-error">{error}</div>}
        <button
          className="btn btn-primary"
          disabled={busy || events.length === 0}
          onClick={handlePublish}
        >
          {busy ? '发布中…' : `发布新版本（快照 ${events.length} 个事件）`}
        </button>
        {events.length === 0 && (
          <div className="alert alert-error" style={{ marginTop: 12 }}>
            暂无事件草稿，无法发布。
          </div>
        )}
      </div>

      <h3>历史版本（{pubs.length}）</h3>
      {pubs.length === 0 ? (
        <div className="empty">尚未发布过任何版本。</div>
      ) : (
        <div className="event-list">
          {pubs.map((p) => (
            <div key={p.id} className="event-item">
              <div className="event-item-main">
                <div className="event-title">v{p.version}</div>
                <div className="event-meta">
                  {p.entry_count} 个事件 · {formatDateTime(p.created_at)}
                  {p.note ? ` · ${p.note}` : ''}
                </div>
              </div>
              <div className="event-item-actions">
                <button
                  className="btn btn-small"
                  onClick={() => onPublished?.(p.id)}
                >
                  前往浏览
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
