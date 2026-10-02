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
  try {
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
  } catch {
    // Speech synthesis not supported — silently ignore
  }
}

/** Map ml_scam_probability to a CSS class for the ring colour. */
function confidenceClass(prob) {
  if (prob >= 70) return 'ai-badge--high'
  if (prob >= 40) return 'ai-badge--medium'
  return 'ai-badge--low'
}

/** Render the SEBI Registry Check badge. */
function RegistryBadge({ registryCheck, t }) {
  if (!registryCheck || registryCheck.status === 'no_number_detected') {
    return null
  }

  const isVerified = registryCheck.status === 'verified'

  return (
    <div
      className={`registry-badge ${isVerified ? 'registry-badge--verified' : 'registry-badge--fake'}`}
      role="status"
      id="registry-check-badge"
    >
      <span className="registry-badge-icon" aria-hidden="true">
        {isVerified ? '✅' : '🚨'}
      </span>
      <div className="registry-badge-content">
        <span className="registry-badge-label">
          {t.verdict.registryCheck || 'SEBI Registry'}
        </span>
        <span className="registry-badge-status">
          {isVerified
            ? (t.verdict.sebiVerified || 'SEBI Number Verified')
            : (t.verdict.sebiFake || 'FAKE SEBI NUMBER DETECTED')}
        </span>
        {isVerified && registryCheck.name ? (
          <span className="registry-badge-entity">
            {registryCheck.name}
            {registryCheck.type ? ` · ${registryCheck.type}` : ''}
          </span>
        ) : null}
        <span className="registry-badge-number">
          {registryCheck.extracted_number}
        </span>
      </div>
    </div>
  )
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
  const mlProb = result.ml_scam_probability

  return (
    <main className={`page verdict-page ${riskClass}`}>
      <h1 className="page-title">{t.verdict.title}</h1>

      <div className="verdict-top-row">
        <p className="verdict-badge" role="status">
          <span className="verdict-icon" aria-hidden="true">
            {riskIcon}
          </span>
          <span>{riskLabel}</span>
        </p>

        {mlProb != null ? (
          <div
            className={`ai-badge ${confidenceClass(mlProb)}`}
            title={`${t.verdict.aiConfidence}: ${mlProb}%`}
          >
            <span className="ai-badge-icon" aria-hidden="true">🤖</span>
            <div className="ai-badge-content">
              <span className="ai-badge-label">{t.verdict.aiConfidence}</span>
              <span className="ai-badge-value">{mlProb}%</span>
            </div>
          </div>
        ) : null}
      </div>

      <RegistryBadge registryCheck={result.registry_check} t={t} />

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
