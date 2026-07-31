import DefaultTheme from 'vitepress/theme'
import { watchEffect } from 'vue'
import { useData, inBrowser } from 'vitepress'
import './custom.css'
import type { Theme } from 'vitepress'

const theme: Theme = {
  extends: DefaultTheme,
  setup() {
    const { lang, dir } = useData()
    watchEffect(() => {
      if (!inBrowser) return
      const isRtl = lang.value === 'fa' || dir.value === 'rtl'
      document.documentElement.lang = lang.value
      document.documentElement.dir = isRtl ? 'rtl' : 'ltr'
      document.documentElement.classList.toggle('fa-rtl', isRtl)
    })
  },
}

export default theme
