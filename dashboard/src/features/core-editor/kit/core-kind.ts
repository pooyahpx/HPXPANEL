import type { CoreResponseType } from '@/service/api'
import { isCredentialVpnKind, isWgFamilyKind } from './credential-vpn-config'

/**
 * Dashboard-local extension until the generated API and core-kit publish the
 * new backend enum values. Run `bun run gen:api` after the backend lands.
 */
export type DashboardCoreKind =
  | 'xray'
  | 'wg'
  | 'wg_c'
  | 'amneziawg'
  | 'ikev2'
  | 'l2tp'
  | 'openvpn'
  | 'pptp'
  | 'openconnect'
  | 'sstp'
  | 'ssh'
  | 'gre'
  | 'mtproto'

export type CoreKindGroupId = 'proxy' | 'wireguard' | 'classicVpn' | 'overlay'

export type CoreKindGroup = {
  id: CoreKindGroupId
  kinds: readonly DashboardCoreKind[]
}

/** Grouped backend kinds for the Core Kind picker UI. */
export const CORE_KIND_GROUPS: readonly CoreKindGroup[] = [
  { id: 'proxy', kinds: ['xray'] },
  { id: 'wireguard', kinds: ['wg', 'wg_c', 'amneziawg'] },
  { id: 'classicVpn', kinds: ['openvpn', 'ikev2', 'l2tp', 'pptp', 'openconnect', 'sstp', 'ssh'] },
  { id: 'overlay', kinds: ['gre', 'mtproto'] },
]

const KIND_SET = new Set<string>([
  'xray',
  'wg',
  'wg_c',
  'amneziawg',
  'ikev2',
  'l2tp',
  'openvpn',
  'pptp',
  'openconnect',
  'sstp',
  'ssh',
  'gre',
  'mtproto',
])

export function apiCoreTypeToKind(type: CoreResponseType | DashboardCoreKind | undefined): DashboardCoreKind {
  if (type && KIND_SET.has(String(type))) return type as DashboardCoreKind
  return 'xray'
}

export function isSupportedCoreEditorKind(type: CoreResponseType | DashboardCoreKind | undefined): boolean {
  if (type == null) return true
  return KIND_SET.has(String(type))
}

export { isCredentialVpnKind, isWgFamilyKind }
