import { Link } from 'react-router-dom'
import { useLanguage } from '../LanguageContext'

export default function Recovery() {
  const { t } = useLanguage()

  return (
    <main className="page recovery-page">
      <h1 className="page-title">{t.recovery.title}</h1>
      <p className="page-subtitle">{t.recovery.subtitle}</p>

      <ol className="recovery-list">
        {t.recovery.steps.map((step, i) => (
          <li key={i} className="recovery-item">
            <span className="recovery-num" aria-hidden="true">
              {i + 1}
            </span>
            <span>{step}</span>
          </li>
        ))}
      </ol>

      <Link to="/" className="btn btn-primary">
        {t.recovery.backHome}
      </Link>
    </main>
  )
}
