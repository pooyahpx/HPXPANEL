import type { CoreResponseType } from '@/service/api'

/**
 * Dashboard-local extension until the generated API and core-kit publish the
 * new backend enum values. Run `bun run gen:api` after the backend lands.
 */
export type DashboardCoreKind = 'xray' | 'wg' | 'ikev2' | 'l2tp' | 'openvpn'

export function apiCoreTypeToKind(type: CoreResponseType | DashboardCoreKind | undefined): DashboardCoreKind {
  if (type === 'wg') return 'wg'
  if (type === 'ikev2') return 'ikev2'
  if (type === 'l2tp') return 'l2tp'
  if (type === 'openvpn') return 'openvpn'
  return 'xray'
}

export function isSupportedCoreEditorKind(type: CoreResponseType | DashboardCoreKind | undefined): boolean {
  return (
    type === 'wg' ||
    type === 'xray' ||
    type === 'ikev2' ||
    type === 'l2tp' ||
    type === 'openvpn' ||
    type == null ||
    type === undefined
  )
}
