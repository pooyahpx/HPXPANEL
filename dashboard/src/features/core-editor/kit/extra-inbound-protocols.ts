/** Inbound protocols stored via Xray unmanaged raw until xray-config-kit supports them. */
export const EXTRA_INBOUND_PROTOCOLS = ['anytls', 'tuic', 'naive'] as const

export type ExtraInboundProtocol = (typeof EXTRA_INBOUND_PROTOCOLS)[number]

export function isExtraInboundProtocol(protocol: string): protocol is ExtraInboundProtocol {
  return (EXTRA_INBOUND_PROTOCOLS as readonly string[]).includes(protocol)
}
