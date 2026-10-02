import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useLanguage } from '../LanguageContext'

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:5000'
const QUESTIONS_URL = `${API_BASE}/api/guided/questions`
const SUBMIT_URL = `${API_BASE}/api/guided`

const ICONS = {
  person_unknown: '👤',
  money_bag: '💰',
  clock: '⏰',
  lock: '🔒',
  bank: '🏦',
  group: '👥',
}

/**
 * Safely speak text via the Web Speech API.
 * Wrapped in try/catch so browsers that don't fully support it won't crash.
 */
function speak(text, lang) {
  try {
    if (!window.speechSynthesis) return
    window.speechSynthesis.cancel()
    const utterance = new SpeechSynthesisUtterance(text)
    utterance.lang = lang === 'hi' ? 'hi-IN' : 'en-IN'
    utterance.rate = 0.9
    window.speechSynthesis.speak(utterance)
  } catch {
    // Speech synthesis not supported or blocked — silently ignore
  }
}

export default function GuidedMode() {
  const { t, language, format } = useLanguage()
  const navigate = useNavigate()
  const [questions, setQuestions] = useState([])
  const [index, setIndex] = useState(0)
  const [answers, setAnswers] = useState([])
  const [loading, setLoading] = useState(true)
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    let cancelled = false

    async function load() {
      setLoading(true)
      setError('')
      setIndex(0)
      setAnswers([])

      try {
        const res = await fetch(`${QUESTIONS_URL}?lang=${language}`)
        if (!res.ok) throw new Error(`HTTP ${res.status}`)
        const data = await res.json()
        if (!cancelled) {
          setQuestions(data.questions || [])
        }
      } catch {
        if (!cancelled) setError(t.guided.error)
      } finally {
        if (!cancelled) setLoading(false)
      }
    }

    load()
    return () => {
      cancelled = true
      try { window.speechSynthesis?.cancel() } catch { /* ignored */ }
    }
  }, [language, t.guided.error])

  async function finish(finalAnswers) {
    setSubmitting(true)
    setError('')
    try {
      const res = await fetch(SUBMIT_URL, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ answers: finalAnswers, language }),
      })
      if (!res.ok) {
        const body = await res.json().catch(() => ({}))
        throw new Error(body.error || `HTTP ${res.status}`)
      }
      const data = await res.json()
      navigate('/verdict', { state: { result: data, source: 'guided' } })
    } catch {
      setError(t.guided.error)
      setSubmitting(false)
    }
  }

  function handleAnswer(yes) {
    if (submitting || !questions[index]) return

    const current = questions[index]
    const nextAnswers = [
      ...answers,
      { id: current.id, answer: yes },
    ]
    setAnswers(nextAnswers)

    if (index + 1 >= questions.length) {
      finish(nextAnswers)
    } else {
      setIndex(index + 1)
    }
  }

  if (loading) {
    return (
      <main className="page guided-page">
        <div className="loading-state">
          <span className="spinner" aria-hidden="true" />
          <p className="page-subtitle">{t.guided.submitting}</p>
        </div>
      </main>
    )
  }

  if (error && questions.length === 0) {
    return (
      <main className="page guided-page">
        <p className="form-error" role="alert">
          {error}
        </p>
      </main>
    )
  }

  const current = questions[index]
  if (!current) return null

  return (
    <main className="page guided-page">
      <h1 className="page-title">{t.guided.title}</h1>
      <p className="guided-progress">
        {format(t.guided.progress, {
          current: index + 1,
          total: questions.length,
        })}
      </p>

      <div className="guided-card">
        <span className="guided-icon" aria-hidden="true">
          {ICONS[current.icon] || '❓'}
        </span>
        <p className="guided-question">{current.text}</p>

        <button
          type="button"
          className="btn btn-secondary"
          onClick={() => speak(current.text, language)}
        >
          🔊 {t.guided.speak}
        </button>
      </div>

      {error ? <p className="form-error" role="alert">{error}</p> : null}

      <div className="guided-actions">
        <button
          type="button"
          className="btn btn-yes"
          disabled={submitting}
          onClick={() => handleAnswer(true)}
        >
          {t.guided.yes}
        </button>
        <button
          type="button"
          className="btn btn-no"
          disabled={submitting}
          onClick={() => handleAnswer(false)}
        >
          {t.guided.no}
        </button>
      </div>

      {submitting ? (
        <div className="loading-state">
          <span className="spinner" aria-hidden="true" />
          <p className="page-subtitle">{t.guided.submitting}</p>
        </div>
      ) : null}
    </main>
  )
}
