export interface PulsePortForwardRow {
  external_port: number
  internal_ip: string
  internal_port: number
}

/** BackPack L3 ports syntax: "443", "443=8443", "443=10.0.0.5:8443" */
export function toBackpackPortString(rule: PulsePortForwardRow): string {
  const ext = rule.external_port
  const intPort = rule.internal_port
  const ip = rule.internal_ip.trim()
  if (ip) return `${ext}=${ip}:${intPort}`
  if (ext === intPort) return String(ext)
  return `${ext}=${intPort}`
}

export function fromBackpackPortString(value: string): PulsePortForwardRow | null {
  const raw = value.trim()
  if (!raw) return null
  const eq = raw.indexOf('=')
  if (eq === -1) {
    const port = Number(raw)
    if (!Number.isInteger(port) || port < 1 || port > 65535) return null
    return { external_port: port, internal_ip: '', internal_port: port }
  }
  const external = Number(raw.slice(0, eq))
  const target = raw.slice(eq + 1)
  const colon = target.lastIndexOf(':')
  if (colon === -1) {
    const internal = Number(target)
    if (!Number.isInteger(external) || !Number.isInteger(internal)) return null
    return { external_port: external, internal_ip: '', internal_port: internal }
  }
  const internal = Number(target.slice(colon + 1))
  const ip = target.slice(0, colon)
  if (!Number.isInteger(external) || !Number.isInteger(internal)) return null
  return { external_port: external, internal_ip: ip, internal_port: internal }
}
