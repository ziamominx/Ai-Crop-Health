import { createContext, useContext, useEffect, useState } from 'react'

const LangContext = createContext(null)

/* Only the UI language preference is stored in localStorage (harmless preference). */
export function LanguageProvider({ children }) {
  const [lang, setLang] = useState(() => localStorage.getItem('agricure_lang') || null)

  useEffect(() => {
    if (lang) localStorage.setItem('agricure_lang', lang)
  }, [lang])

  const t = (key) => {
    const dict = lang ? TR_REF[lang] : null
    return (dict && dict[key]) || TR_REF.en[key] || key
  }

  return (
    <LangContext.Provider value={{ lang, setLang, t, langReady: !!lang }}>
      {children}
    </LangContext.Provider>
  )
}

import { TR } from '../i18n/translations.js'
const TR_REF = TR

export function useLanguage() {
  return useContext(LangContext)
}
