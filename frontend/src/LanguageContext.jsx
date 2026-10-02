import { createContext, useContext, useMemo, useState } from 'react'
import en from './i18n/en.json'
import hi from './i18n/hi.json'

const dictionaries = { en, hi }

const LanguageContext = createContext(null)

export function LanguageProvider({ children }) {
  const [language, setLanguage] = useState('en')

  const value = useMemo(() => {
    const t = dictionaries[language] || dictionaries.en

    function toggleLanguage() {
      setLanguage((prev) => (prev === 'en' ? 'hi' : 'en'))
    }

    /** Replace {{key}} placeholders in a string. */
    function format(template, vars = {}) {
      if (!template) return ''
      return template.replace(/\{\{(\w+)\}\}/g, (_, key) =>
        vars[key] !== undefined ? String(vars[key]) : '',
      )
    }

    return {
      language,
      setLanguage,
      toggleLanguage,
      t,
      format,
    }
  }, [language])

  return (
    <LanguageContext.Provider value={value}>
      {children}
    </LanguageContext.Provider>
  )
}

export function useLanguage() {
  const ctx = useContext(LanguageContext)
  if (!ctx) {
    throw new Error('useLanguage must be used within LanguageProvider')
  }
  return ctx
}
