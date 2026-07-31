import { defineConfig } from 'vitepress'

const enSidebar = [
  {
    text: 'Start',
    items: [
      { text: 'Introduction', link: '/en/introduction' },
      { text: 'Installation', link: '/en/installation' },
      { text: 'Install from source', link: '/en/source' },
    ],
  },
  {
    text: 'Panel',
    items: [
      { text: 'Features', link: '/en/features' },
      { text: 'Users & limits', link: '/en/users' },
      { text: 'Subscriptions', link: '/en/subscriptions' },
    ],
  },
  {
    text: 'Protocols',
    items: [
      { text: 'Overview', link: '/en/protocols/overview' },
      { text: 'L2TP & IKEv2 / IPsec', link: '/en/protocols/ipsec' },
    ],
  },
]

const faSidebar = [
  {
    text: 'شروع',
    items: [
      { text: 'مقدمه', link: '/fa/introduction' },
      { text: 'نصب', link: '/fa/installation' },
      { text: 'نصب از سورس', link: '/fa/source' },
    ],
  },
  {
    text: 'پنل',
    items: [
      { text: 'ویژگی‌ها', link: '/fa/features' },
      { text: 'کاربران و محدودیت‌ها', link: '/fa/users' },
      { text: 'سابسکریپشن', link: '/fa/subscriptions' },
    ],
  },
  {
    text: 'پروتکل‌ها',
    items: [
      { text: 'نمای کلی', link: '/fa/protocols/overview' },
      { text: 'L2TP و IKEv2 / IPsec', link: '/fa/protocols/ipsec' },
    ],
  },
]

const ruSidebar = [
  {
    text: 'Старт',
    items: [
      { text: 'Введение', link: '/ru/introduction' },
      { text: 'Установка', link: '/ru/installation' },
      { text: 'Из исходников', link: '/ru/source' },
    ],
  },
  {
    text: 'Панель',
    items: [
      { text: 'Возможности', link: '/ru/features' },
      { text: 'Пользователи и лимиты', link: '/ru/users' },
      { text: 'Подписки', link: '/ru/subscriptions' },
    ],
  },
  {
    text: 'Протоколы',
    items: [
      { text: 'Обзор', link: '/ru/protocols/overview' },
      { text: 'L2TP и IKEv2 / IPsec', link: '/ru/protocols/ipsec' },
    ],
  },
]

export default defineConfig({
  title: 'HPXPANEL',
  description: 'Command-deck proxy operations console — documentation',
  base: '/HPXPANEL/',
  cleanUrls: true,
  lastUpdated: true,
  ignoreDeadLinks: true,

  head: [
    ['link', { rel: 'icon', href: '/HPXPANEL/hpx-logo.svg', type: 'image/svg+xml' }],
    ['meta', { name: 'theme-color', content: '#0ea5e9' }],
  ],

  themeConfig: {
    logo: '/hpx-logo.svg',
    siteTitle: 'HPXPANEL',
    socialLinks: [{ icon: 'github', link: 'https://github.com/pooyahpx/HPXPANEL' }],
    search: { provider: 'local' },
    footer: {
      message: 'dev by <a href="https://github.com/pooyahpx">hpx</a>',
      copyright: 'HPXPANEL documentation',
    },
  },

  locales: {
    root: {
      label: 'English',
      lang: 'en',
      themeConfig: {
        nav: [
          { text: 'Introduction', link: '/en/introduction' },
          { text: 'Install', link: '/en/installation' },
          { text: 'IPsec', link: '/en/protocols/ipsec' },
          { text: 'GitHub', link: 'https://github.com/pooyahpx/HPXPANEL' },
        ],
        sidebar: {
          '/en/': enSidebar,
          '/': enSidebar,
        },
        outline: { label: 'On this page' },
      },
    },
    fa: {
      label: 'فارسی',
      lang: 'fa',
      link: '/fa/',
      dir: 'rtl',
      themeConfig: {
        nav: [
          { text: 'مقدمه', link: '/fa/introduction' },
          { text: 'نصب', link: '/fa/installation' },
          { text: 'IPsec', link: '/fa/protocols/ipsec' },
          { text: 'GitHub', link: 'https://github.com/pooyahpx/HPXPANEL' },
        ],
        sidebar: { '/fa/': faSidebar },
        outline: { label: 'در این صفحه' },
        darkModeSwitchLabel: 'تم',
        sidebarMenuLabel: 'منو',
        returnToTopLabel: 'بازگشت به بالا',
        docFooter: { prev: 'قبلی', next: 'بعدی' },
      },
    },
    ru: {
      label: 'Русский',
      lang: 'ru',
      link: '/ru/',
      themeConfig: {
        nav: [
          { text: 'Введение', link: '/ru/introduction' },
          { text: 'Установка', link: '/ru/installation' },
          { text: 'IPsec', link: '/ru/protocols/ipsec' },
          { text: 'GitHub', link: 'https://github.com/pooyahpx/HPXPANEL' },
        ],
        sidebar: { '/ru/': ruSidebar },
        outline: { label: 'На этой странице' },
        docFooter: { prev: 'Назад', next: 'Далее' },
      },
    },
  },
})
