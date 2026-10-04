import { useCallback, useEffect, useRef, useState } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { useLanguage } from '../LanguageContext'

const API_URL = `${import.meta.env.VITE_API_URL || `http://${window.location.hostname}:5000`}/api/analyze`

export default function MessageInput() {
  const { t, language } = useLanguage()
  const navigate = useNavigate()
  const [searchParams, setSearchParams] = useSearchParams()
  const [text, setText] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const autoSubmitDone = useRef(false)

  // ── Core submit logic (no event needed) ───────────────────────────
  const submitText = useCallback(
    async (input) => {
      const trimmed = input.trim()
      if (!trimmed) return

      setLoading(true)
      setError('')

      try {
        const res = await fetch(API_URL, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ text: trimmed, language }),
        })

        if (!res.ok) {
          const body = await res.json().catch(() => ({}))
          throw new Error(body.error || `HTTP ${res.status}`)
        }

        const data = await res.json()
        navigate('/verdict', { state: { result: data, source: 'message' } })
      } catch {
        setError(t.message.error)
      } finally {
        setLoading(false)
      }
    },
    [language, navigate, t],
  )

  // ── Read shared text from URL query params ────────────────────────
  useEffect(() => {
    try {
      // DEBUG: Log the raw URL and parsed query parameters
      console.log('[Web Share Target] Raw URL:', window.location.href)
      console.log('[Web Share Target] Parsed Params:', Object.fromEntries(searchParams.entries()))

      // Handle URL encoding safely (searchParams.get decodes once, but this handles double-encoding often seen in WhatsApp shares)
      const safeDecode = (val) => {
        if (!val) return ''
        try {
          return decodeURIComponent(val)
        } catch (e) {
          return val
        }
      }

      const sharedText = safeDecode(searchParams.get('text'))
      const sharedTitle = safeDecode(searchParams.get('title'))
      const sharedUrl = safeDecode(searchParams.get('url'))

      // Combine all parts (WhatsApp typically sends text + url)
      const parts = [sharedTitle, sharedText, sharedUrl].filter(Boolean)
      const combined = parts.join('\n').trim()

      console.log('[Web Share Target] Extracted String:', combined)

      if (combined) {
        setText(combined)

        // Clean the URL so a page refresh won't re-trigger
        setSearchParams({}, { replace: true })

        // Auto-submit after a brief delay so the user sees the textarea fill
        // Safeguard: Check that text exists and hasn't been submitted yet
        if (!autoSubmitDone.current) {
          autoSubmitDone.current = true
          const timer = setTimeout(() => submitText(combined), 600)
          return () => clearTimeout(timer)
        }
      }
    } catch (err) {
      // Malformed URL params should never crash the app
      console.error('[Web Share Target] Failed to parse share params:', err)
    }
  }, [searchParams, setSearchParams, submitText])

  function handleSubmit(e) {
    e.preventDefault()
    submitText(text)
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
          {loading ? (
            <>
              <span className="spinner" aria-hidden="true" /> {t.message.checking}
            </>
          ) : (
            t.message.submit
          )}
        </button>
      </form>
    </main>
  )
}
