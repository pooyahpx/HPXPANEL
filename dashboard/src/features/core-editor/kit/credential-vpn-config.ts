export type CredentialVpnCoreKind = 'pptp' | 'openconnect' | 'sstp' | 'ssh' | 'gre' | 'mtproto'

export interface CredentialVpnCoreConfig {
  inbound_tag: string
  server_addr: string
  port: number
  pool?: string
  dns: string[]
  protocol?: string
  banner?: string
  peer_addr?: string
  local_addr?: string
  ipsec?: boolean
  fou_port?: number
  secret?: string
  mode?: string
}

const DEFAULTS: Record<CredentialVpnCoreKind, CredentialVpnCoreConfig> = {
  pptp: {
    inbound_tag: 'pptp',
    server_addr: '',
    port: 1723,
    pool: '10.30.0.0/24',
    dns: ['1.1.1.1', '8.8.8.8'],
  },
  openconnect: {
    inbound_tag: 'openconnect',
    server_addr: '0.0.0.0',
    port: 443,
    pool: '10.31.0.0/24',
    dns: ['1.1.1.1', '8.8.8.8'],
    protocol: 'anyconnect',
  },
  sstp: {
    inbound_tag: 'sstp',
    server_addr: '0.0.0.0',
    port: 443,
    pool: '10.32.0.0/24',
    dns: ['1.1.1.1', '8.8.8.8'],
  },
  ssh: {
    inbound_tag: 'ssh',
    server_addr: '0.0.0.0',
    port: 22,
    dns: [],
    banner: '',
  },
  gre: {
    inbound_tag: 'gre',
    server_addr: '0.0.0.0',
    port: 0,
    pool: '10.33.0.0/24',
    dns: ['1.1.1.1', '8.8.8.8'],
    peer_addr: '',
    local_addr: '',
    ipsec: false,
  },
  mtproto: {
    inbound_tag: 'mtproto',
    server_addr: '0.0.0.0',
    port: 443,
    dns: [],
    secret: '',
    mode: 'dd',
  },
}

export function createDefaultCredentialVpnConfig(kind: CredentialVpnCoreKind): CredentialVpnCoreConfig {
  return JSON.parse(JSON.stringify(DEFAULTS[kind])) as CredentialVpnCoreConfig
}

function stringValue(value: unknown): string {
  return typeof value === 'string' ? value : ''
}

function stringArray(value: unknown): string[] {
  return Array.isArray(value) ? value.filter((item): item is string => typeof item === 'string') : []
}

function intValue(value: unknown, fallback: number): number {
  return typeof value === 'number' && Number.isFinite(value) ? value : fallback
}

export function normalizeCredentialVpnConfig(kind: CredentialVpnCoreKind, value: unknown): CredentialVpnCoreConfig {
  const defaults = createDefaultCredentialVpnConfig(kind)
  const config = value && typeof value === 'object' && !Array.isArray(value) ? (value as Record<string, unknown>) : {}

  return {
    ...defaults,
    inbound_tag: stringValue(config.inbound_tag) || defaults.inbound_tag,
    server_addr: stringValue(config.server_addr) || defaults.server_addr,
    port: intValue(config.port, defaults.port),
    pool: config.pool === undefined ? defaults.pool : stringValue(config.pool),
    dns: config.dns === undefined ? defaults.dns : stringArray(config.dns),
    protocol: stringValue(config.protocol) || defaults.protocol,
    banner: stringValue(config.banner),
    peer_addr: stringValue(config.peer_addr),
    local_addr: stringValue(config.local_addr),
    ipsec: typeof config.ipsec === 'boolean' ? config.ipsec : defaults.ipsec,
    fou_port:
      config.fou_port === undefined || config.fou_port === null || config.fou_port === ''
        ? undefined
        : intValue(config.fou_port, 0) || undefined,
    secret: stringValue(config.secret),
    mode: stringValue(config.mode) || defaults.mode,
  }
}

export function credentialVpnConfigToPersist(kind: CredentialVpnCoreKind, config: CredentialVpnCoreConfig): Record<string, unknown> {
  const out: Record<string, unknown> = {
    inbound_tag: config.inbound_tag,
    server_addr: config.server_addr,
    port: config.port,
    dns: config.dns,
  }
  if (kind !== 'ssh' && kind !== 'mtproto') {
    out.pool = config.pool
  }
  if (kind === 'openconnect') out.protocol = config.protocol || 'anyconnect'
  if (kind === 'ssh' && config.banner) out.banner = config.banner
  if (kind === 'gre') {
    out.peer_addr = config.peer_addr
    if (config.local_addr) out.local_addr = config.local_addr
    out.ipsec = Boolean(config.ipsec)
    if (config.fou_port) out.fou_port = config.fou_port
  }
  if (kind === 'mtproto') {
    out.secret = config.secret
    out.mode = config.mode || 'dd'
  }
  return out
}

export function validateCredentialVpnConfig(
  kind: CredentialVpnCoreKind,
  config: CredentialVpnCoreConfig,
): Array<{ path: string; messageKey: string }> {
  const issues: Array<{ path: string; messageKey: string }> = []
  if (!config.inbound_tag.trim()) issues.push({ path: 'inbound_tag', messageKey: 'validation.required' })
  if (kind !== 'pptp' && !config.server_addr.trim()) issues.push({ path: 'server_addr', messageKey: 'validation.required' })
  if (kind !== 'ssh' && kind !== 'mtproto' && !String(config.pool ?? '').trim()) {
    issues.push({ path: 'pool', messageKey: 'validation.required' })
  }
  if (kind === 'gre' && !String(config.peer_addr ?? '').trim()) issues.push({ path: 'peer_addr', messageKey: 'validation.required' })
  if (kind === 'mtproto' && String(config.secret ?? '').trim().length < 16) {
    issues.push({ path: 'secret', messageKey: 'validation.required' })
  }
  return issues
}

export function isCredentialVpnKind(kind: string | undefined): kind is CredentialVpnCoreKind {
  return kind === 'pptp' || kind === 'openconnect' || kind === 'sstp' || kind === 'ssh' || kind === 'gre' || kind === 'mtproto'
}

export function isWgFamilyKind(kind: string | undefined): boolean {
  return kind === 'wg' || kind === 'wg_c' || kind === 'amneziawg'
}
