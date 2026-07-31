import DefaultTheme from 'vitepress/theme'
import { watchEffect, nextTick } from 'vue'
import { useData, inBrowser } from 'vitepress'
import './custom.css'
import type { Theme } from 'vitepress'

function applyDir(isRtl: boolean, lang: string) {
  const html = document.documentElement
  html.lang = lang
  html.dir = isRtl ? 'rtl' : 'ltr'
  html.classList.toggle('fa-rtl', isRtl)
  html.classList.toggle('is-ltr', !isRtl)
  document.body?.classList.toggle('fa-rtl', isRtl)
}

const theme: Theme = {
  extends: DefaultTheme,
  setup() {
    const { lang, dir } = useData()
    watchEffect(async () => {
      if (!inBrowser) return
      const isRtl = lang.value === 'fa' || dir.value === 'rtl'
      applyDir(isRtl, lang.value)
      await nextTick()
      applyDir(isRtl, lang.value)
    })
  },
}

export default theme
