import DefaultTheme from 'vitepress/theme'
import { watchEffect, nextTick } from 'vue'
import { useData, inBrowser } from 'vitepress'
import './custom.css'
import type { Theme } from 'vitepress'

function applyRtl(isRtl: boolean) {
  const html = document.documentElement
  html.dir = isRtl ? 'rtl' : 'ltr'
  html.classList.toggle('fa-rtl', isRtl)
  document.body?.classList.toggle('fa-rtl', isRtl)
}

const theme: Theme = {
  extends: DefaultTheme,
  setup() {
    const { lang, dir } = useData()
    watchEffect(async () => {
      if (!inBrowser) return
      const isRtl = dir.value === 'rtl' || lang.value === 'fa'
      applyRtl(isRtl)
      htmlLang(lang.value)
      await nextTick()
      applyRtl(isRtl)
    })
  },
}

function htmlLang(lang: string) {
  document.documentElement.lang = lang
}

export default theme
