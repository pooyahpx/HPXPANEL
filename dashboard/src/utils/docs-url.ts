import { DOCUMENTATION } from '@/constants/Project'
import i18n from '@/locales/i18n'

const docsBase = () => DOCUMENTATION.replace(/\/$/, '')

/**
 * Documentation URL for a panel route.
 * HPXPANEL docs: pooyahpx.github.io/HPXPANEL/{locale}/…
 */
export function getDocsUrl(pagePath: string): string {
  const locale = i18n.language || 'en'
  const normalizedLocale = ['en', 'fa', 'ru'].includes(locale.split('-')[0]) ? locale.split('-')[0] : 'en'
  const base = `${docsBase()}/${normalizedLocale}`

  if (pagePath.startsWith('/hpx-tunnel') || pagePath.startsWith('/nodes')) {
    return `${base}/protocols/overview`
  }
  if (pagePath.startsWith('/users') || pagePath.startsWith('/admins') || pagePath.startsWith('/admin-roles')) {
    return `${base}/users`
  }
  if (pagePath.startsWith('/templates') || pagePath.startsWith('/hosts') || pagePath.startsWith('/groups') || pagePath.startsWith('/bulk')) {
    return `${base}/subscriptions`
  }
  if (pagePath.startsWith('/settings') || pagePath === '/' || pagePath.startsWith('/statistics') || pagePath.startsWith('/api-keys')) {
    return `${base}/features`
  }

  return `${base}/`
}
