import { useEffect } from 'react'
import { Link, useLocation, useNavigate } from 'react-router-dom'
import { useLanguage } from '../LanguageContext'

const RISK_CLASS = {
  high: 'verdict-high',
  careful: 'verdict-careful',
  looks_okay: 'verdict-okay',
  cant_tell: 'verdict-unknown',
}

const RISK_ICON = {
  high: '⚠️',
  careful: '⚡',
  looks_okay: '✅',
  cant_tell: '❔',
}

function speakVerdict(result, t, language) {
  if (!window.speechSynthesis || !result) return
  window.speechSynthesis.cancel()

  const riskLabel = t.verdict.risk[result.risk_level] || result.risk_level
  const reasons = (result.flags || []).map((f) => f.reason).join('. ')
  const steps = (result.next_steps || []).join('. ')
  const text = [riskLabel, reasons, steps, result.disclaimer]
    .filter(Boolean)
    .join('. ')

  const utterance = new SpeechSynthesisUtterance(text)
  utterance.lang = language === 'hi' ? 'hi-IN' : 'en-IN'
  utterance.rate = 0.9
  window.speechSynthesis.speak(utterance)
}

export default function Verdict() {
  const { t, language } = useLanguage()
  const location = useLocation()
  const navigate = useNavigate()
  const result = location.state?.result

  useEffect(() => {
    if (!result) {
      navigate('/', { replace: true })
    }
    return () => window.speechSynthesis?.cancel()
  }, [result, navigate])

  if (!result) return null

  const riskClass = RISK_CLASS[result.risk_level] || RISK_CLASS.cant_tell
  const riskIcon = RISK_ICON[result.risk_level] || RISK_ICON.cant_tell
  const riskLabel =
    t.verdict.risk[result.risk_level] || result.risk_level

  return (
    <main className={`page verdict-page ${riskClass}`}>
      <h1 className="page-title">{t.verdict.title}</h1>
      <p className="verdict-badge" role="status">
        <span className="verdict-icon" aria-hidden="true">
          {riskIcon}
        </span>
        <span>{riskLabel}</span>
      </p>

      <button
        type="button"
        className="btn btn-speak"
        onClick={() => speakVerdict(result, t, language)}
      >
        <span className="speak-icon" aria-hidden="true">
          🔊
        </span>
        {t.verdict.speak}
      </button>

      {result.flags?.length > 0 ? (
        <section className="verdict-section">
          <h2>{t.verdict.why}</h2>
          <ul className="flag-list">
            {result.flags.map((flag) => (
              <li key={flag.id} className="flag-item">
                {flag.reason}
              </li>
            ))}
          </ul>
        </section>
      ) : null}

      {result.could_not_verify?.length > 0 ? (
        <section className="verdict-section">
          <h2>{t.verdict.couldNotVerify}</h2>
          <ul className="flag-list">
            {result.could_not_verify.map((item) => (
              <li key={item} className="flag-item">
                {item}
              </li>
            ))}
          </ul>
        </section>
      ) : null}

      {result.next_steps?.length > 0 ? (
        <section className="verdict-section">
          <h2>{t.verdict.nextSteps}</h2>
          <ol className="steps-list">
            {result.next_steps.map((step) => (
              <li key={step}>{step}</li>
            ))}
          </ol>
        </section>
      ) : null}

      {result.disclaimer ? (
        <p className="disclaimer">{result.disclaimer}</p>
      ) : null}

      <div className="verdict-actions">
        <Link to="/message" className="btn btn-primary">
          {t.verdict.checkAnother}
        </Link>
        <Link to="/" className="btn btn-secondary">
          {t.verdict.backHome}
        </Link>
      </div>
    </main>
  )
}
