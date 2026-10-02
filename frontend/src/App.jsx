import { BrowserRouter, Link, Route, Routes } from 'react-router-dom'
import { LanguageProvider, useLanguage } from './LanguageContext'
import Home from './components/Home'
import MessageInput from './components/MessageInput'
import GuidedMode from './components/GuidedMode'
import Verdict from './components/Verdict'
import Recovery from './components/Recovery'
import './App.css'

function Header() {
  const { t, toggleLanguage } = useLanguage()

  return (
    <header className="app-header">
      <Link to="/" className="brand">
        <span className="brand-name">{t.appName}</span>
        <span className="brand-tagline">{t.tagline}</span>
      </Link>
      <button
        type="button"
        className="lang-toggle"
        onClick={toggleLanguage}
        aria-label="Toggle language"
      >
        {t.languageToggle}
      </button>
    </header>
  )
}

function AppRoutes() {
  return (
    <div className="app-shell">
      <Header />
      <Routes>
        <Route path="/" element={<Home />} />
        <Route path="/message" element={<MessageInput />} />
        <Route path="/guided" element={<GuidedMode />} />
        <Route path="/verdict" element={<Verdict />} />
        <Route path="/recovery" element={<Recovery />} />
      </Routes>
    </div>
  )
}

export default function App() {
  return (
    <LanguageProvider>
      <BrowserRouter>
        <AppRoutes />
      </BrowserRouter>
    </LanguageProvider>
  )
}
