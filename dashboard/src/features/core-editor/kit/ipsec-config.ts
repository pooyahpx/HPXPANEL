export type IpsecCoreKind = 'ikev2' | 'l2tp'

export interface IpsecCoreConfig {
  inbound_tag: string
  server_addr: string
  identity?: string
  psk?: string
  pool: string
  local_ip?: string
  egress_interface: string
  dns: string[]
  ike_proposals: string[]
  esp_proposals: string[]
  ca_cert?: string
  server_cert?: string
  server_key?: string
}

const DEFAULT_IKE_PROPOSALS = ['aes256-sha256-modp2048']
const DEFAULT_ESP_PROPOSALS = ['aes256-sha256']

export function createDefaultIpsecConfig(kind: IpsecCoreKind): IpsecCoreConfig {
  const common = {
    inbound_tag: kind,
    server_addr: '0.0.0.0',
    pool: kind === 'ikev2' ? '10.20.0.0/24' : '10.21.0.0/24',
    egress_interface: '',
    dns: ['1.1.1.1', '8.8.8.8'],
    ike_proposals: [...DEFAULT_IKE_PROPOSALS],
    esp_proposals: [...DEFAULT_ESP_PROPOSALS],
  }

  return kind === 'ikev2'
    ? {
        ...common,
        identity: '',
        ca_cert: '',
        server_cert: '',
        server_key: '',
      }
    : {
        ...common,
        psk: '',
        local_ip: '10.21.0.1',
      }
}

function stringValue(value: unknown): string {
  return typeof value === 'string' ? value : ''
}

function stringArray(value: unknown): string[] {
  return Array.isArray(value) ? value.filter((item): item is string => typeof item === 'string') : []
}

export function normalizeIpsecConfig(kind: IpsecCoreKind, value: unknown): IpsecCoreConfig {
  const defaults = createDefaultIpsecConfig(kind)
  const config = value && typeof value === 'object' && !Array.isArray(value) ? (value as Record<string, unknown>) : {}

  return {
    ...defaults,
    inbound_tag: stringValue(config.inbound_tag) || defaults.inbound_tag,
    server_addr: stringValue(config.server_addr) || defaults.server_addr,
    pool: stringValue(config.pool) || defaults.pool,
    egress_interface: stringValue(config.egress_interface),
    dns: config.dns === undefined ? defaults.dns : stringArray(config.dns),
    ike_proposals: config.ike_proposals === undefined ? defaults.ike_proposals : stringArray(config.ike_proposals),
    esp_proposals: config.esp_proposals === undefined ? defaults.esp_proposals : stringArray(config.esp_proposals),
    ...(kind === 'ikev2'
      ? {
          identity: stringValue(config.identity),
          ca_cert: stringValue(config.ca_cert),
          server_cert: stringValue(config.server_cert),
          server_key: stringValue(config.server_key),
        }
      : {
          psk: stringValue(config.psk),
          local_ip: stringValue(config.local_ip) || defaults.local_ip,
        }),
  }
}

export function validateIpsecConfig(kind: IpsecCoreKind, config: IpsecCoreConfig): Array<{ path: string; messageKey: string }> {
  const required: Array<keyof IpsecCoreConfig> = ['inbound_tag', 'server_addr', 'pool', 'egress_interface']
  if (kind === 'ikev2') required.push('identity', 'ca_cert', 'server_cert', 'server_key')
  else required.push('psk', 'local_ip')

  const issues = required.filter(key => !String(config[key] ?? '').trim()).map(path => ({ path, messageKey: 'validation.required' }))

  if (!config.dns.length) issues.push({ path: 'dns', messageKey: 'validation.required' })
  if (!config.ike_proposals.length) issues.push({ path: 'ike_proposals', messageKey: 'validation.required' })
  if (!config.esp_proposals.length) issues.push({ path: 'esp_proposals', messageKey: 'validation.required' })

  return issues
}
