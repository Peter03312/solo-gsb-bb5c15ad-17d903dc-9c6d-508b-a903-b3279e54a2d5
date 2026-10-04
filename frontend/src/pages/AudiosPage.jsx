import { Fragment, useEffect, useRef, useState } from 'react'
import { api, formatBytes, formatDateTime, formatTime } from '../api.js'

export default function AudiosPage() {
  const [audios, setAudios] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [file, setFile] = useState(null)
  const [transcriptMode, setTranscriptMode] = useState('none') // none | file | text
  const [transcriptText, setTranscriptText] = useState('')
  const [transcriptFile, setTranscriptFile] = useState(null)
  const [uploading, setUploading] = useState(false)
  const [expanded, setExpanded] = useState({})
  const [detailTranscripts, setDetailTranscripts] = useState({})
  const fileRef = useRef(null)
  const trFileRef = useRef(null)

  const load = async () => {
    setLoading(true)
    try {
      setAudios(await api.listAudios())
      setError(null)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { load() }, [])

  const resetForm = () => {
    setFile(null)
    setTranscriptMode('none')
    setTranscriptText('')
    setTranscriptFile(null)
    if (fileRef.current) fileRef.current.value = ''
    if (trFileRef.current) trFileRef.current.value = ''
  }

  const handleUpload = async () => {
    if (!file) {
      setError('请选择 MP3 / WAV 音频文件')
      return
    }
    const lower = file.name.toLowerCase()
    if (!lower.endsWith('.mp3') && !lower.endsWith('.wav')) {
      setError('仅支持 MP3 / WAV 音频文件')
      return
    }
    setError(null)
    setUploading(true)
    try {
      const fd = new FormData()
      fd.append('file', file)
      if (transcriptMode === 'text' && transcriptText) {
        fd.append('transcript_text', transcriptText)
      }
      if (transcriptMode === 'file' && transcriptFile) {
        fd.append('transcript_file', transcriptFile)
      }
      await api.uploadAudio(fd)
      resetForm()
      await load()
    } catch (err) {
      setError(err.message)
    } finally {
      setUploading(false)
    }
  }

  const handleDelete = async (a) => {
    if (!window.confirm(`确定删除音频「${a.original_name}」？`)) return
    try {
      await api.deleteAudio(a.id)
      await load()
    } catch (err) {
      window.alert(err.message)
    }
  }

  const toggleTranscript = async (id) => {
    if (expanded[id]) {
      setExpanded((e) => ({ ...e, [id]: false }))
      return
    }
    if (!detailTranscripts[id]) {
      try {
        const detail = await api.getAudio(id)
        setDetailTranscripts((d) => ({ ...d, [id]: detail.transcript_text || '' }))
      } catch (err) {
        window.alert(err.message)
        return
      }
    }
    setExpanded((e) => ({ ...e, [id]: true }))
  }

  if (loading) return <div className="empty">加载中…</div>

  return (
    <div>
      <h2>音频库</h2>

      <div className="upload-panel">
        <h4>上传音频与逐字稿</h4>
        <div className="form-row">
          <label>音频文件（MP3 / WAV，≤ 200MB）*</label>
          <input
            ref={fileRef}
            type="file"
            accept=".mp3,.wav,audio/mpeg,audio/wav"
            onChange={(e) => setFile(e.target.files[0] || null)}
          />
        </div>
        <div className="form-row">
          <label>逐字稿（可选，UTF-8 文本，≤ 5MB）</label>
          <div className="radio-row">
            <label>
              <input type="radio" checked={transcriptMode === 'none'}
                onChange={() => setTranscriptMode('none')} /> 不上传
            </label>
            <label>
              <input type="radio" checked={transcriptMode === 'text'}
                onChange={() => setTranscriptMode('text')} /> 粘贴文本
            </label>
            <label>
              <input type="radio" checked={transcriptMode === 'file'}
                onChange={() => setTranscriptMode('file')} /> 上传 .txt
            </label>
          </div>
          {transcriptMode === 'text' && (
            <textarea
              rows={5}
              value={transcriptText}
              onChange={(e) => setTranscriptText(e.target.value)}
              placeholder="将逐字稿内容粘贴于此……"
            />
          )}
          {transcriptMode === 'file' && (
            <input
              ref={trFileRef}
              type="file"
              accept=".txt,text/plain"
              onChange={(e) => setTranscriptFile(e.target.files[0] || null)}
            />
          )}
        </div>
        {error && <div className="alert alert-error">{error}</div>}
        <button className="btn btn-primary" disabled={uploading} onClick={handleUpload}>
          {uploading ? '上传中…失败会自动清理，请稍候' : '上传'}
        </button>
      </div>

      {audios.length === 0 ? (
        <div className="empty">音频库为空，先上传一段采访录音吧。</div>
      ) : (
        <table className="table">
          <thead>
            <tr>
              <th>文件名</th>
              <th>时长</th>
              <th>大小</th>
              <th>上传时间</th>
              <th>逐字稿</th>
              <th>操作</th>
            </tr>
          </thead>
          <tbody>
            {audios.map((a) => (
              <Fragment key={a.id}>
                <tr>
                  <td>{a.original_name}</td>
                  <td>{formatTime(a.duration)}</td>
                  <td>{formatBytes(a.size_bytes)}</td>
                  <td>{formatDateTime(a.created_at)}</td>
                  <td>
                    <button className="btn-link" onClick={() => toggleTranscript(a.id)}>
                      {expanded[a.id] ? '收起' : '查看'}
                    </button>
                  </td>
                  <td>
                    <button
                      className="btn btn-small btn-danger-outline"
                      onClick={() => handleDelete(a)}
                    >
                      删除
                    </button>
                  </td>
                </tr>
                {expanded[a.id] && (
                  <tr className="transcript-row">
                    <td colSpan={6}>
                      <pre className="transcript-pre">
                        {detailTranscripts[a.id] || '（该音频暂无逐字稿）'}
                      </pre>
                    </td>
                  </tr>
                )}
              </Fragment>
            ))}
          </tbody>
        </table>
      )}
    </div>
  )
}
