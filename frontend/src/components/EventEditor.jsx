import { useEffect, useMemo, useState } from 'react'
import { api, formatTime } from '../api.js'
import ConflictDialog from './ConflictDialog.jsx'

const emptyForm = () => ({
  title: '',
  event_date: new Date().toISOString().slice(0, 10),
  description: '',
  quotes: [],
})

export default function EventEditor({ event: initialEvent, audios, onPlay, onSaved, onCancel }) {
  const editing = !!initialEvent
  const [form, setForm] = useState(() => {
    if (!initialEvent) return emptyForm()
    return {
      title: initialEvent.title,
      event_date: initialEvent.event_date,
      description: initialEvent.description,
      quotes: initialEvent.quotes.map((q) => ({
        audio_id: q.audio_id,
        speaker: q.speaker || '',
        start_sec: q.start_sec,
        end_sec: q.end_sec,
        quote_text: q.quote_text || '',
      })),
    }
  })
  const [baseRevision, setBaseRevision] = useState(initialEvent?.revision ?? null)
  const [error, setError] = useState('')
  const [conflict, setConflict] = useState(null)
  const [saving, setSaving] = useState(false)

  const audioMap = useMemo(() => {
    const m = {}
    for (const a of audios) m[a.id] = a
    return m
  }, [audios])

  const update = (key, value) => setForm((f) => ({ ...f, [key]: value }))

  const updateQuote = (idx, key, value) => {
    setForm((f) => ({
      ...f,
      quotes: f.quotes.map((q, i) => (i === idx ? { ...q, [key]: value } : q)),
    }))
  }

  const addQuote = () => {
    const firstAudio = audios[0]?.id
    setForm((f) => ({
      ...f,
      quotes: [
        ...f.quotes,
        {
          audio_id: firstAudio ?? '',
          speaker: '',
          start_sec: 0,
          end_sec: firstAudio ? Math.min(5, audioMap[firstAudio]?.duration || 5) : 0,
          quote_text: '',
        },
      ],
    }))
  }

  const removeQuote = (idx) => {
    setForm((f) => ({ ...f, quotes: f.quotes.filter((_, i) => i !== idx) }))
  }

  // 客户端前置校验，与服务端规则保持一致，避免明显无效请求
  const validate = () => {
    if (!form.title.trim()) return '请填写事件标题'
    if (!/^\d{4}-\d{2}-\d{2}$/.test(form.event_date)) return '请选择有效的事件日期'
    if (isNaN(Date.parse(form.event_date))) return '事件日期无效'
    if (form.quotes.length === 0) return '至少需要一条引文'
    for (let i = 0; i < form.quotes.length; i++) {
      const q = form.quotes[i]
      if (!q.audio_id) return `第 ${i + 1} 条引文：请选择音频`
      const s = Number(q.start_sec)
      const e = Number(q.end_sec)
      if (Number.isNaN(s) || Number.isNaN(e) || s < 0 || e < 0) {
        return `第 ${i + 1} 条引文：起止秒须为非负数字`
      }
      if (s >= e) return `第 ${i + 1} 条引文：起始秒须小于结束秒`
      const audio = audioMap[q.audio_id]
      if (!audio) return `第 ${i + 1} 条引文：所选音频已不存在，请重选`
      if (audio.duration != null && e > audio.duration + 0.1) {
        return `第 ${i + 1} 条引文：结束秒超出音频时长 ${formatTime(audio.duration)}`
      }
    }
    return ''
  }

  const buildPayload = (revision = baseRevision) => ({
    title: form.title,
    event_date: form.event_date,
    description: form.description,
    base_revision: revision,
    quotes: form.quotes.map((q) => ({
      audio_id: Number(q.audio_id),
      speaker: q.speaker,
      start_sec: Number(q.start_sec),
      end_sec: Number(q.end_sec),
      quote_text: q.quote_text,
    })),
  })

  const submit = async (overrideRevision) => {
    const msg = validate()
    if (msg) {
      setError(msg)
      return
    }
    setError('')
    setSaving(true)
    try {
      const payload = buildPayload(overrideRevision)
      const saved = editing
        ? await api.updateEvent(initialEvent.id, payload)
        : await api.createEvent(payload)
      setBaseRevision(saved.revision)
      onSaved(saved)
    } catch (err) {
      if (err.status === 409 && err.conflict) {
        setConflict(err.conflict)
      } else {
        setError(err.message)
      }
    } finally {
      setSaving(false)
    }
  }

  if (audios.length === 0) {
    return (
      <div className="empty">
        音频库中还没有音频。请先到「音频库」上传 MP3 / WAV，再来创建事件与引文。
      </div>
    )
  }

  return (
    <div className="editor">
      <div className="form-row">
        <label>事件标题 *</label>
        <input
          type="text"
          value={form.title}
          maxLength={300}
          onChange={(e) => update('title', e.target.value)}
          placeholder="例如：1938 年文庙藏经迁移"
        />
      </div>
      <div className="form-row">
        <label>事件日期 *</label>
        <input
          type="date"
          value={form.event_date}
          onChange={(e) => update('event_date', e.target.value)}
        />
      </div>
      <div className="form-row">
        <label>事件说明</label>
        <textarea
          rows={3}
          value={form.description}
          onChange={(e) => update('description', e.target.value)}
          placeholder="背景、出处、整理者备注……"
        />
      </div>

      <div className="quotes-head">
        <h4>引文（同一事件的多种说法并列展示，共 {form.quotes.length} 条）</h4>
        <button className="btn" onClick={addQuote}>＋ 添加引文</button>
      </div>

      {form.quotes.map((q, idx) => {
        const audio = audioMap[q.audio_id]
        return (
          <div key={idx} className="quote-card">
            <div className="quote-card-head">
              <span className="quote-index">说法 #{idx + 1}</span>
              <button className="btn-link danger" onClick={() => removeQuote(idx)}>
                删除该引文
              </button>
            </div>
            <div className="quote-grid">
              <label>
                来源音频 *
                <select
                  value={q.audio_id}
                  onChange={(e) => updateQuote(idx, 'audio_id', Number(e.target.value))}
                >
                  {audios.map((a) => (
                    <option key={a.id} value={a.id}>
                      {a.original_name}（{formatTime(a.duration)}）
                    </option>
                  ))}
                </select>
              </label>
              <label>
                讲述人
                <input
                  type="text"
                  value={q.speaker}
                  maxLength={200}
                  onChange={(e) => updateQuote(idx, 'speaker', e.target.value)}
                  placeholder="姓名 / 称谓"
                />
              </label>
              <label>
                起始秒 *
                <input
                  type="number"
                  min="0"
                  step="0.1"
                  value={q.start_sec}
                  onChange={(e) => updateQuote(idx, 'start_sec', e.target.value)}
                />
              </label>
              <label>
                结束秒 *
                <input
                  type="number"
                  min="0"
                  step="0.1"
                  value={q.end_sec}
                  onChange={(e) => updateQuote(idx, 'end_sec', e.target.value)}
                />
                {audio && (
                  <small className="muted">时长 {formatTime(audio.duration)}</small>
                )}
              </label>
            </div>
            <div className="quote-actions">
              <button
                type="button"
                className="btn btn-small"
                disabled={!audio}
                onClick={() => onPlay(q.audio_id, Number(q.start_sec) || 0,
                  `${audio?.original_name || ''} · ${q.speaker || '佚名'}`)}
              >
                ▶ 从起始秒试听
              </button>
            </div>
            <label>
              引文文字（摘自逐字稿）
              <textarea
                rows={2}
                value={q.quote_text}
                maxLength={5000}
                onChange={(e) => updateQuote(idx, 'quote_text', e.target.value)}
              />
            </label>
          </div>
        )
      })}

      {error && <div className="alert alert-error">{error}</div>}

      <div className="editor-actions">
        <button className="btn" onClick={onCancel}>取消</button>
        <button className="btn btn-primary" disabled={saving} onClick={() => submit()}>
          {saving ? '保存中…' : editing ? `保存修订（当前 v${baseRevision}）` : '创建事件'}
        </button>
      </div>

      {conflict && (
        <ConflictDialog
          conflict={conflict}
          onCancel={() => {
            setConflict(null)
            onSaved(conflict.server_event)
          }}
          onRetry={(payload) => {
            setConflict(null)
            submit(payload.base_revision)
          }}
        />
      )}
    </div>
  )
}
