import { useQuery } from '@tanstack/react-query'

interface CachedRelease {
  version: string
  url: string
  timestamp: number
}

interface VersionCheckResult {
  hasUpdate: boolean
  latestVersion: string | null
  currentVersion: string | null
  releaseUrl: string | null
  isLoading: boolean
}

interface UseVersionCheckOptions {
  enabled?: boolean
}

const GITHUB_API_URL = 'https://api.github.com/repos/pooyahpx/HPXPANEL/releases/latest'
const CACHE_KEY = 'hpx_release'
const CACHE_DURATION = 10 * 60 * 1000

interface ParsedSemver {
  major: number
  minor: number
  patch: number
  prerelease: string[]
}

function parseSemver(version: string): ParsedSemver {
  const cleaned = version.replace(/^v/i, '').trim()
  const [main = '0', prerelease = ''] = cleaned.split('-', 2)
  const [major = 0, minor = 0, patch = 0] = main.split('.').map(part => parseInt(part, 10) || 0)
  return {
    major,
    minor,
    patch,
    prerelease: prerelease ? prerelease.split('.') : [],
  }
}

function comparePrerelease(a: string[], b: string[]): number {
  if (a.length === 0 && b.length === 0) return 0
  if (a.length === 0) return 1
  if (b.length === 0) return -1

  const len = Math.max(a.length, b.length)
  for (let i = 0; i < len; i += 1) {
    const av = a[i]
    const bv = b[i]
    if (av === undefined) return -1
    if (bv === undefined) return 1

    const an = Number(av)
    const bn = Number(bv)
    const aIsNum = !Number.isNaN(an) && String(an) === av
    const bIsNum = !Number.isNaN(bn) && String(bn) === bv

    if (aIsNum && bIsNum) {
      if (an < bn) return -1
      if (an > bn) return 1
    } else if (aIsNum !== bIsNum) {
      return aIsNum ? -1 : 1
    } else if (av < bv) {
      return -1
    } else if (av > bv) {
      return 1
    }
  }
  return 0
}

function compareVersions(current: string, latest: string): number {
  const a = parseSemver(current)
  const b = parseSemver(latest)

  for (const key of ['major', 'minor', 'patch'] as const) {
    if (a[key] < b[key]) return -1
    if (a[key] > b[key]) return 1
  }

  return comparePrerelease(a.prerelease, b.prerelease)
}

function getCached(): CachedRelease | null {
  try {
    const cached = localStorage.getItem(CACHE_KEY)
    if (!cached) return null
    return JSON.parse(cached)
  } catch {
    return null
  }
}

function setCache(version: string, url: string): void {
  try {
    const data: CachedRelease = { version, url, timestamp: Date.now() }
    localStorage.setItem(CACHE_KEY, JSON.stringify(data))
  } catch {
    return
  }
}

async function fetchLatestRelease(): Promise<{ version: string; url: string } | null> {
  const cached = getCached()
  if (cached && Date.now() - cached.timestamp < CACHE_DURATION) {
    return { version: cached.version, url: cached.url }
  }

  try {
    const response = await fetch(GITHUB_API_URL, {
      referrerPolicy: 'no-referrer',
      credentials: 'omit',
      headers: { Accept: 'application/vnd.github.v3+json' },
    })

    if (!response.ok) {
      return cached ? { version: cached.version, url: cached.url } : null
    }

    const data = await response.json()
    const version = data.tag_name?.replace(/^v/i, '') || ''
    const url = data.html_url || ''

    if (version) setCache(version, url)
    return { version, url }
  } catch {
    return cached ? { version: cached.version, url: cached.url } : null
  }
}

export function useVersionCheck(currentVersion: string | null, options: UseVersionCheckOptions = {}): VersionCheckResult {
  const enabled = options.enabled ?? true
  const { data, isLoading } = useQuery({
    queryKey: ['github-release-check'],
    queryFn: fetchLatestRelease,
    enabled,
    staleTime: CACHE_DURATION,
    gcTime: CACHE_DURATION * 2,
    refetchOnWindowFocus: false,
    refetchOnMount: false,
    refetchInterval: CACHE_DURATION,
    retry: 1,
  })

  const latestVersion = data?.version || null
  const cleanCurrentVersion = currentVersion?.replace(/^v/i, '') || null

  const hasUpdate = enabled && !!(cleanCurrentVersion && latestVersion && compareVersions(cleanCurrentVersion, latestVersion) < 0)

  return {
    hasUpdate,
    latestVersion: enabled ? latestVersion : null,
    currentVersion: cleanCurrentVersion,
    releaseUrl: enabled ? data?.url || null : null,
    isLoading: enabled ? isLoading : false,
  }
}
