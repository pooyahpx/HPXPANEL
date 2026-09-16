import { useQuery } from '@tanstack/react-query'

interface CachedRelease {
  version: string
  url: string
  timestamp: number
}

interface NodeReleaseResult {
  latestVersion: string | null
  releaseUrl: string | null
  isLoading: boolean
  hasUpdate: (currentVersion: string | null) => boolean
}

const GITHUB_API_URL = 'https://api.github.com/repos/pooyahpx/HPXNODE/releases/latest'
const CACHE_KEY = 'pg_node_release_v2'
const CACHE_DURATION = 10 * 60 * 1000

/** Semantic-ish compare for node versions (e.g. 0.5.2 vs 0.6.0). Returns -1 / 0 / 1. */
export function compareNodeVersions(current: string, latest: string): number {
  const currentParts = current
    .trim()
    .replace(/^v/i, '')
    .split(/[\.-]/)
    .filter(p => !isNaN(Number(p)))
    .map(Number)
  const latestParts = latest
    .trim()
    .replace(/^v/i, '')
    .split(/[\.-]/)
    .filter(p => !isNaN(Number(p)))
    .map(Number)

  for (let i = 0; i < Math.max(currentParts.length, latestParts.length); i++) {
    const curr = currentParts[i] || 0
    const lat = latestParts[i] || 0
    if (curr < lat) return -1
    if (curr > lat) return 1
  }
  return 0
}

/** Panel Update Node needs management API on API Port (HPXNODE ≥ 0.6.2 in-container). */
export const MIN_HOST_AGENT_VERSION = '0.6.2'

export function needsHostAgentForUpdate(nodeVersion: string | null | undefined): boolean {
  if (!nodeVersion) return false
  return compareNodeVersions(nodeVersion, MIN_HOST_AGENT_VERSION) < 0
}

export const HOST_AGENT_UPDATE_COMMAND =
  'sudo bash -c "$(curl -fsSL https://github.com/pooyahpx/HPXNODE/raw/v0.6.2/scripts/install.sh)" @ update -y'

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

async function fetchLatestNodeRelease(): Promise<{ version: string; url: string } | null> {
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
    const version = data.tag_name?.trim().replace(/^v/i, '') || ''
    const url = data.html_url || ''

    if (version) setCache(version, url)
    return { version, url }
  } catch {
    return cached ? { version: cached.version, url: cached.url } : null
  }
}

export function useNodeReleases(): NodeReleaseResult {
  const { data, isLoading } = useQuery({
    queryKey: ['github-node-release-check-v2'],
    queryFn: fetchLatestNodeRelease,
    staleTime: CACHE_DURATION,
    gcTime: CACHE_DURATION * 2,
    refetchOnWindowFocus: false,
    refetchOnMount: true,
    refetchInterval: CACHE_DURATION,
    retry: 1,
  })

  const hasUpdate = (currentVersion: string | null) => {
    if (!currentVersion || !data?.version) return false
    const cleanCurrent = currentVersion.trim().replace(/^v/i, '')
    const cleanLatest = data.version.trim().replace(/^v/i, '')
    return compareNodeVersions(cleanCurrent, cleanLatest) < 0
  }

  return {
    latestVersion: data?.version || null,
    releaseUrl: data?.url || null,
    isLoading,
    hasUpdate,
  }
}
