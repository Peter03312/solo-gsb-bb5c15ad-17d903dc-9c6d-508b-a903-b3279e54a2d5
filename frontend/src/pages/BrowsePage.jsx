import { useEffect, useState } from 'react'
import { api, formatDateTime, formatTime } from '../api.js'

// 编年浏览：选择已发布版本（不可变）或查看当前草稿；同一事件多种说法并列展示。
export default function BrowsePage({ onPlay, versionId, versionConsumed }) {
  const [pubs, setPubs] = useState([])
  const [mode, setMode] = useState('') // '' | pub-<id> | 'draft'
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    api.listPublications().then(setPubs).catch((e) => setError(e.message))
  }, [])

  // 发布页可指定跳转到新版本
  useEffect(() => {
    if (versionId) {
      setMode(`pub-${versionId}`)
      versionConsumed?.()
    }
  }, [versionId])

  // 默认选中最新发布版
  useEffect(() => {
    if (!mode && pubs.length) setMode(`pub-${pubs[0].id}`)
  }, [pubs])

  useEffect(() => {
    if (!mode) return
    setLoading(true)
    setError('')
    setData(null)
    const promise = mode === 'draft'
      ? Promise.resolve({ draft: true, entries: null }).then(async (x) => {
        const evs = await api.listEvents()
        return {
          draft: true,
          note: '',
          created_at: '',
          entries: evs.map((e) => ({
            event_id: e.id,
            event_title: e.title,
            event_date: e.event_date,
            event_description: e.description,
            event_revision: e.revision,
            entry_type: e.quotes.length > 1 ? 'multiple' : 'single',
            quotes: e.quotes.map((q) => ({
              audio_id: q.audio_id,
              audio_name: q.audio_name,
              speaker: q.speaker,
              start_sec: q.start_sec,
              end_sec: q.end_sec,
              quote_text: q.quote_text,
            })),
          })),
        }
      })
      : api.getPublication(Number(mode.replace('pub-', '')))
    promise.then(setData).catch((e) => setError(e.message)).finally(() => setLoading(false))
  }, [mode])

  return (
    <div>
      <div className="page-head">
        <h2>编年浏览</h2>
        <select value={mode} onChange={(e) => setMode(e.target.value)}>
          {pubs.length === 0 && <option value="">（暂无发布版）</option>}
          {pubs.map((p) => (
            <option key={p.id} value={`pub-${p.id}`}>
              发布版 v{p.version}（{p.created_at.slice(0, 10)}）
            </option>
          ))}
          <option value="draft">当前草稿（可继续修订）</option>
        </select>
      </div>

      {data && !data.draft && (
        <div className="pub-banner">
          📌 正在浏览不可变发布版 · {formatDateTime(data.created_at)}
          {data.note ? ` · 备注：${data.note}` : ''}
        </div>
      )}
      {data?.draft && (
        <div className="pub-banner pub-banner-draft">
          ✏️ 正在浏览当前草稿，内容可能随时被修订；已发布版本不受影响。
        </div>
      )}

      {loading && <div className="empty">加载中…</div>}
      {error && <div className="alert alert-error">{error}</div>}
      {!mode && !loading && (
        <div className="empty">还没有可浏览的内容。请先整理事件并发布。</div>
      )}

      {data && (
        <div className="timeline">
          {data.entries.map((entry, idx) => (
            <div key={`${entry.event_id}-${idx}`} className="timeline-item">
              <div className="timeline-date">{entry.event_date}</div>
              <div className="timeline-body">
                <h3 className="timeline-title">
                  {entry.event_title}
                  {entry.entry_type === 'multiple' && (
                    <span className="badge">多种说法 · {entry.quotes.length} 条</span>
                  )}
                  <span className="badge badge-muted">草稿 v{entry.event_revision}</span>
                </h3>
                {entry.event_description && (
                  <p className="event-description">{entry.event_description}</p>
                )}
                <div className={entry.entry_type === 'multiple'
                  ? 'quotes-grid'
                  : 'quotes-single'}
                >
                  {entry.quotes.map((q, qi) => (
                    <div key={qi} className="quote-view">
                      <div className="quote-view-head">
                        <span className="quote-speaker">🎙️ {q.speaker || '佚名讲述人'}</span>
                        <span className="muted">{q.audio_name}</span>
                      </div>
                      <blockquote className="quote-text">
                        {q.quote_text || '（无引文文字）'}
                      </blockquote>
                      <button
                        className="btn btn-small"
                        onClick={() => onPlay(
                          q.audio_id,
                          q.start_sec,
                          `${q.audio_name} · ${q.speaker || '佚名'}`,
                        )}
                      >
                        ▶ 跳转原音 {formatTime(q.start_sec)} – {formatTime(q.end_sec)}
                      </button>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          ))}
          {data.entries.length === 0 && <div className="empty">该视图下暂无事件。</div>}
        </div>
      )}
    </div>
  )
}
