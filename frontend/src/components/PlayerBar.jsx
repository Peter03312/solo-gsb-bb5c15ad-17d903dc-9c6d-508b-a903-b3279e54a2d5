import { forwardRef, useEffect, useImperativeHandle, useRef } from 'react'
import { formatTime } from '../api.js'

// 全局底部播放器：引文点击后加载对应音频并跳到起始秒。
const PlayerBar = forwardRef(function PlayerBar({ target, onClose }, ref) {
  const audioRef = useRef(null)
  const lastUrl = useRef(null)

  useImperativeHandle(ref, () => ({
    seekTo(sec) {
      const el = audioRef.current
      if (!el) return
      const doSeek = () => {
        el.currentTime = sec
        el.play().catch(() => {})
      }
      if (el.readyState >= 1) doSeek()
      else el.addEventListener('loadedmetadata', doSeek, { once: true })
    },
  }))

  useEffect(() => {
    const el = audioRef.current
    if (!el || target.url === lastUrl.current) return
    lastUrl.current = target.url
    el.load()
    const doSeek = () => {
      el.currentTime = target.startSec
      el.play().catch(() => {})
    }
    el.addEventListener('loadedmetadata', doSeek, { once: true })
  }, [target])

  return (
    <div className="player-bar">
      <div className="player-meta" title={target.label}>
        🔊 {target.label}
        <span className="player-hint">（已跳转至 {formatTime(target.startSec)}）</span>
      </div>
      <audio
        ref={audioRef}
        src={target.url}
        controls
        preload="metadata"
        style={{ flex: 1, minWidth: 0 }}
      />
      <button className="btn btn-ghost" onClick={onClose}>收起</button>
    </div>
  )
})

export default PlayerBar
