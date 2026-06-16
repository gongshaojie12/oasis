// =========== Copyright 2026 @ WANXIANG. All Rights Reserved. ===========
// react-i18next bootstrap. Language persists in localStorage so the
// preference survives reloads. ``switchLang`` is the one mutator and
// also keeps ``<html lang>`` in sync for screen readers.
import i18n from 'i18next'
import { initReactI18next } from 'react-i18next'
import zh from '../locales/zh.json'
import en from '../locales/en.json'

const LANG_KEY = 'wanxiang.lang'

function detectInitialLang(): 'zh' | 'en' {
  const saved = localStorage.getItem(LANG_KEY)
  if (saved === 'zh' || saved === 'en') return saved
  if (typeof navigator !== 'undefined' && navigator.language?.toLowerCase().startsWith('en')) {
    return 'en'
  }
  return 'zh'
}

void i18n.use(initReactI18next).init({
  resources: { zh: { translation: zh }, en: { translation: en } },
  lng: detectInitialLang(),
  fallbackLng: 'zh',
  interpolation: { escapeValue: false },
})

export function switchLang(lang: 'zh' | 'en') {
  void i18n.changeLanguage(lang)
  localStorage.setItem(LANG_KEY, lang)
  if (typeof document !== 'undefined') {
    document.documentElement.lang = lang === 'en' ? 'en' : 'zh-CN'
  }
}

export default i18n
