import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useLanguage } from '../LanguageContext'

const API_URL = 'http://localhost:5000/api/analyze'

export default function MessageInput() {
  const { t, language } = useLanguage()
  const navigate = useNavigate()
  const [text, setText] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  async function handleSubmit(e) {
    e.preventDefault()
    const trimmed = text.trim()
    if (!trimmed || loading) return

    setLoading(true)
    setError('')

    try {
      const res = await fetch(API_URL, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text: trimmed, language }),
      })

      if (!res.ok) {
        throw new Error(`HTTP ${res.status}`)
      }

      const data = await res.json()
      navigate('/verdict', { state: { result: data, source: 'message' } })
    } catch {
      setError(t.message.error)
    } finally {
      setLoading(false)
    }
  }

  return (
    <main className="page message-page">
      <h1 className="page-title">{t.message.title}</h1>

      <form className="message-form" onSubmit={handleSubmit}>
        <label className="sr-only" htmlFor="message-text">
          {t.message.title}
        </label>
        <textarea
          id="message-text"
          className="message-textarea"
          value={text}
          onChange={(e) => setText(e.target.value)}
          placeholder={t.message.placeholder}
          rows={8}
          required
        />

        {error ? <p className="form-error" role="alert">{error}</p> : null}

        <button
          type="submit"
          className="btn btn-primary"
          disabled={loading || !text.trim()}
        >
          {loading ? t.message.checking : t.message.submit}
        </button>
      </form>
    </main>
  )
}
