import i18n from 'i18next'
import LanguageDetector from 'i18next-browser-languagedetector'
import HttpApi from 'i18next-http-backend'
import { initReactI18next } from 'react-i18next'
import { joinURL } from 'ufo'

i18n
  .use(LanguageDetector)
  .use(initReactI18next)
  .use(HttpApi)
  .init(
    {
      debug: import.meta.env.NODE_ENV === 'development',
      returnNull: false,
      fallbackLng: 'en',
      // All four languages after filling critical ru/zh namespaces from en.
      // Note: ru/zh newly filled namespaces (openvpn, hpxPulse, hpxTunnel, observability,
      // audit, copilot, settings.backup, etc.) may still be English until translated.
      supportedLngs: ['en', 'fa', 'ru', 'zh'],
      interpolation: {
        escapeValue: false,
      },
      react: {
        useSuspense: true,
      },
      load: 'languageOnly',
      detection: {
        caches: ['localStorage'],
      },
      backend: {
        loadPath: joinURL(import.meta.env.BASE_URL, `statics/locales/{{lng}}.json`),
      },
    },
    function (err) {
      if (err) {
        console.error('i18next initialization error:', err)
      }
      const lang = i18n.language
      document.documentElement.lang = lang
      document.documentElement.setAttribute('dir', i18n.dir())
    },
  )

export default i18n
