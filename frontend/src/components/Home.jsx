import { Link } from 'react-router-dom'
import { useLanguage } from '../LanguageContext'

const PATHS = [
  {
    to: '/message',
    titleKey: 'messageCheck',
    descKey: 'messageCheckDesc',
    icon: '💬',
    className: 'path-card path-message',
  },
  {
    to: '/guided',
    titleKey: 'guidedMode',
    descKey: 'guidedModeDesc',
    icon: '✅',
    className: 'path-card path-guided',
  },
  {
    to: '/recovery',
    titleKey: 'recovery',
    descKey: 'recoveryDesc',
    icon: '🆘',
    className: 'path-card path-recovery',
  },
]

export default function Home() {
  const { t } = useLanguage()

  return (
    <main className="page home-page">
      <h1 className="page-title">{t.home.title}</h1>
      <p className="page-subtitle">{t.home.subtitle}</p>

      <nav className="path-list" aria-label={t.home.title}>
        {PATHS.map((path) => (
          <Link key={path.to} to={path.to} className={path.className}>
            <span className="path-icon" aria-hidden="true">
              {path.icon}
            </span>
            <span className="path-text">
              <span className="path-title">{t.home[path.titleKey]}</span>
              <span className="path-desc">{t.home[path.descKey]}</span>
            </span>
          </Link>
        ))}
      </nav>
    </main>
  )
}
