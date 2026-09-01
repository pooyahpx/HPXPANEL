export interface OpenVPNCoreConfig {
  inbound_tag: string
  port: number
  proto: string
  device: string
  server_subnet: string
  dns: string[]
  cipher: string
  data_ciphers: string[]
  auth: string
  keepalive: string
  max_clients: number
  duplicate_cn: boolean
  push: string[]
  extra_server_directives: string[]
  ca_cert: string
  ca_key?: string
  server_cert: string
  server_key: string
  tls_crypt_key: string
  listeners: Array<{ port: number; proto: string }>
}

export type OpenVPNProtoPreset = 'udp-1194' | 'tcp-443' | 'tcp-1194'

export const OPENVPN_PROTO_PRESETS: Record<
  OpenVPNProtoPreset,
  { proto: 'udp' | 'tcp'; port: number; labelKey: string; hintKey: string }
> = {
  'udp-1194': {
    proto: 'udp',
    port: 1194,
    labelKey: 'coreEditor.openvpn.protoPresets.udp1194',
    hintKey: 'coreEditor.openvpn.protoPresets.udp1194Hint',
  },
  'tcp-443': {
    proto: 'tcp',
    port: 443,
    labelKey: 'coreEditor.openvpn.protoPresets.tcp443',
    hintKey: 'coreEditor.openvpn.protoPresets.tcp443Hint',
  },
  'tcp-1194': {
    proto: 'tcp',
    port: 1194,
    labelKey: 'coreEditor.openvpn.protoPresets.tcp1194',
    hintKey: 'coreEditor.openvpn.protoPresets.tcp1194Hint',
  },
}

export function resolveOpenVPNProtoPreset(proto: string, port: number): OpenVPNProtoPreset | 'custom' {
  const normalized = proto.trim().toLowerCase()
  for (const [key, preset] of Object.entries(OPENVPN_PROTO_PRESETS) as Array<
    [OpenVPNProtoPreset, (typeof OPENVPN_PROTO_PRESETS)[OpenVPNProtoPreset]]
  >) {
    if (preset.proto === normalized && preset.port === port) return key
  }
  return 'custom'
}

export function applyOpenVPNProtoPreset(preset: OpenVPNProtoPreset): Pick<OpenVPNCoreConfig, 'proto' | 'port'> {
  const selected = OPENVPN_PROTO_PRESETS[preset]
  return { proto: selected.proto, port: selected.port }
}

export function createDefaultOpenVPNConfig(): OpenVPNCoreConfig {
  return {
    inbound_tag: 'openvpn',
    port: 1194,
    proto: 'udp',
    device: 'tun',
    server_subnet: '10.29.0.0/16',
    dns: ['1.1.1.1', '8.8.8.8'],
    cipher: 'AES-256-GCM',
    data_ciphers: [],
    auth: 'SHA256',
    keepalive: '10 60',
    max_clients: 1024,
    duplicate_cn: false,
    push: [],
    extra_server_directives: [],
    ca_cert: '',
    ca_key: '',
    server_cert: '',
    server_key: '',
    tls_crypt_key: '',
    listeners: [],
  }
}

function stringValue(value: unknown): string {
  return typeof value === 'string' ? value : ''
}

function numberValue(value: unknown, fallback: number): number {
  return typeof value === 'number' && Number.isFinite(value) ? value : fallback
}

function boolValue(value: unknown, fallback: boolean): boolean {
  return typeof value === 'boolean' ? value : fallback
}

function stringArray(value: unknown): string[] {
  return Array.isArray(value) ? value.filter((item): item is string => typeof item === 'string') : []
}

function listenersArray(value: unknown): Array<{ port: number; proto: string }> {
  if (!Array.isArray(value)) return []
  return value
    .filter((item): item is Record<string, unknown> => !!item && typeof item === 'object' && !Array.isArray(item))
    .map(item => ({
      port: numberValue(item.port, 1194),
      proto: stringValue(item.proto) || 'udp',
    }))
}

export function normalizeOpenVPNConfig(value: unknown): OpenVPNCoreConfig {
  const defaults = createDefaultOpenVPNConfig()
  const config = value && typeof value === 'object' && !Array.isArray(value) ? (value as Record<string, unknown>) : {}

  return {
    ...defaults,
    inbound_tag: stringValue(config.inbound_tag) || defaults.inbound_tag,
    port: numberValue(config.port, defaults.port),
    proto: stringValue(config.proto) || defaults.proto,
    device: stringValue(config.device) || defaults.device,
    server_subnet: stringValue(config.server_subnet) || defaults.server_subnet,
    dns: config.dns === undefined ? defaults.dns : stringArray(config.dns),
    cipher: stringValue(config.cipher) || defaults.cipher,
    data_ciphers: config.data_ciphers === undefined ? defaults.data_ciphers : stringArray(config.data_ciphers),
    auth: stringValue(config.auth) || defaults.auth,
    keepalive: stringValue(config.keepalive) || defaults.keepalive,
    max_clients: numberValue(config.max_clients, defaults.max_clients),
    duplicate_cn: boolValue(config.duplicate_cn, defaults.duplicate_cn),
    push: config.push === undefined ? defaults.push : stringArray(config.push),
    extra_server_directives:
      config.extra_server_directives === undefined ? defaults.extra_server_directives : stringArray(config.extra_server_directives),
    ca_cert: stringValue(config.ca_cert),
    ca_key: stringValue(config.ca_key),
    server_cert: stringValue(config.server_cert),
    server_key: stringValue(config.server_key),
    tls_crypt_key: stringValue(config.tls_crypt_key),
    listeners: config.listeners === undefined ? defaults.listeners : listenersArray(config.listeners),
  }
}

export function validateOpenVPNConfig(config: OpenVPNCoreConfig): Array<{ path: string; messageKey: string }> {
  const required: Array<keyof OpenVPNCoreConfig> = ['inbound_tag', 'server_subnet', 'ca_cert', 'server_cert', 'server_key']
  const issues = required
    .filter(key => !String(config[key] ?? '').trim())
    .map(path => ({ path, messageKey: 'validation.required' }))

  if (!config.port || config.port < 1 || config.port > 65535) {
    issues.push({ path: 'port', messageKey: 'validation.required' })
  }
  if (!config.dns.length) issues.push({ path: 'dns', messageKey: 'validation.required' })

  return issues
}
