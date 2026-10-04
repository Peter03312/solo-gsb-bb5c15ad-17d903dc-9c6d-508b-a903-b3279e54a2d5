import { formatTime } from '../api.js'

// 并发冲突对照弹窗：左为服务器最新版本，右为本人提交内容，可选择放弃或覆盖重试。
export default function ConflictDialog({ conflict, onCancel, onRetry }) {
  const server = conflict?.server_event
  const submitted = conflict?.submitted
  if (!server || !submitted) return null

  const renderQuotes = (quotes) => (
    <div className="diff-quotes">
      {quotes.map((q, i) => (
        <div key={i} className="diff-quote">
          <div>#{i + 1} · 音频 #{q.audio_id} · {q.speaker || '佚名'}</div>
          <div>{formatTime(q.start_sec)} – {formatTime(q.end_sec)}</div>
          <div className="muted">{q.quote_text || '（无引文文字）'}</div>
        </div>
      ))}
    </div>
  )

  return (
    <div className="modal-backdrop">
      <div className="modal modal-wide">
        <h3>⚠️ 并发修改冲突</h3>
        <p className="muted">
          该事件在您编辑期间已被他人保存（版本 v{server.revision}）。
          请对照两侧内容：放弃本地修改，或以当前内容覆盖最新版本重试。
        </p>
        <div className="diff-grid">
          <div className="diff-col">
            <h4>服务器最新版本（v{server.revision}）</h4>
            <div className="diff-field">标题：{server.title}</div>
            <div className="diff-field">日期：{server.event_date}</div>
            <div className="diff-field">{server.description}</div>
            {renderQuotes(server.quotes)}
          </div>
          <div className="diff-col">
            <h4>您的提交内容</h4>
            <div className="diff-field">标题：{submitted.title}</div>
            <div className="diff-field">日期：{submitted.event_date}</div>
            <div className="diff-field">{submitted.description}</div>
            {renderQuotes(submitted.quotes)}
          </div>
        </div>
        <div className="modal-actions">
          <button className="btn" onClick={onCancel}>放弃，采用最新版本</button>
          <button
            className="btn btn-primary"
            onClick={() => onRetry({ ...submitted, base_revision: server.revision })}
          >
            以我的内容覆盖重试
          </button>
        </div>
      </div>
    </div>
  )
}
