export type InfraLocation = {
  countryCode: string | null
  countryEn: string | null
  countryFa: string | null
  flag: string | null
  datacenter: string | null
}

type CountryMeta = {
  code: string
  en: string
  fa: string
  flag: string
  aliases: string[]
}

const COUNTRIES: CountryMeta[] = [
  { code: 'NL', en: 'Netherlands', fa: 'هلند', flag: '🇳🇱', aliases: ['netherlands', 'holland', 'amsterdam', 'ams'] },
  { code: 'DE', en: 'Germany', fa: 'آلمان', flag: '🇩🇪', aliases: ['germany', 'deutschland', 'frankfurt', 'fra', 'falkenstein', 'nuremberg', 'berlin'] },
  { code: 'FR', en: 'France', fa: 'فرانسه', flag: '🇫🇷', aliases: ['france', 'paris', 'par'] },
  { code: 'GB', en: 'United Kingdom', fa: 'انگلستان', flag: '🇬🇧', aliases: ['uk', 'britain', 'england', 'london', 'lon'] },
  { code: 'US', en: 'United States', fa: 'آمریکا', flag: '🇺🇸', aliases: ['usa', 'america', 'newyork', 'nyc', 'losangeles', 'lax', 'seattle', 'miami', 'dallas', 'chicago', 'ashburn'] },
  { code: 'TR', en: 'Turkey', fa: 'ترکیه', flag: '🇹🇷', aliases: ['turkey', 'turkiye', 'istanbul', 'ankara', 'izmir'] },
  { code: 'FI', en: 'Finland', fa: 'فنلاند', flag: '🇫🇮', aliases: ['finland', 'helsinki', 'hel'] },
  { code: 'SE', en: 'Sweden', fa: 'سوئد', flag: '🇸🇪', aliases: ['sweden', 'stockholm'] },
  { code: 'NO', en: 'Norway', fa: 'نروژ', flag: '🇳🇴', aliases: ['norway', 'oslo'] },
  { code: 'PL', en: 'Poland', fa: 'لهستان', flag: '🇵🇱', aliases: ['poland', 'warsaw'] },
  { code: 'CZ', en: 'Czechia', fa: 'چک', flag: '🇨🇿', aliases: ['czech', 'czechia', 'prague'] },
  { code: 'AT', en: 'Austria', fa: 'اتریش', flag: '🇦🇹', aliases: ['austria', 'vienna'] },
  { code: 'CH', en: 'Switzerland', fa: 'سوئیس', flag: '🇨🇭', aliases: ['switzerland', 'swiss', 'zurich', 'sw'] },
  { code: 'IT', en: 'Italy', fa: 'ایتالیا', flag: '🇮🇹', aliases: ['italy', 'milan', 'rome'] },
  { code: 'ES', en: 'Spain', fa: 'اسپانیا', flag: '🇪🇸', aliases: ['spain', 'madrid', 'barcelona'] },
  { code: 'PT', en: 'Portugal', fa: 'پرتغال', flag: '🇵🇹', aliases: ['portugal', 'lisbon'] },
  { code: 'IE', en: 'Ireland', fa: 'ایرلند', flag: '🇮🇪', aliases: ['ireland', 'dublin'] },
  { code: 'BE', en: 'Belgium', fa: 'بلژیک', flag: '🇧🇪', aliases: ['belgium', 'brussels'] },
  { code: 'RU', en: 'Russia', fa: 'روسیه', flag: '🇷🇺', aliases: ['russia', 'moscow', 'spb'] },
  { code: 'UA', en: 'Ukraine', fa: 'اوکراین', flag: '🇺🇦', aliases: ['ukraine', 'kyiv', 'kiev'] },
  { code: 'AE', en: 'UAE', fa: 'امارات', flag: '🇦🇪', aliases: ['uae', 'dubai', 'emirates'] },
  { code: 'SG', en: 'Singapore', fa: 'سنگاپور', flag: '🇸🇬', aliases: ['singapore', 'sgp'] },
  { code: 'JP', en: 'Japan', fa: 'ژاپن', flag: '🇯🇵', aliases: ['japan', 'tokyo'] },
  { code: 'KR', en: 'South Korea', fa: 'کره جنوبی', flag: '🇰🇷', aliases: ['korea', 'seoul'] },
  { code: 'HK', en: 'Hong Kong', fa: 'هنگ‌کنگ', flag: '🇭🇰', aliases: ['hongkong'] },
  { code: 'IN', en: 'India', fa: 'هند', flag: '🇮🇳', aliases: ['india', 'mumbai', 'delhi'] },
  { code: 'CA', en: 'Canada', fa: 'کانادا', flag: '🇨🇦', aliases: ['canada', 'toronto', 'montreal'] },
  { code: 'BR', en: 'Brazil', fa: 'برزیل', flag: '🇧🇷', aliases: ['brazil', 'saopaulo'] },
  { code: 'AU', en: 'Australia', fa: 'استرالیا', flag: '🇦🇺', aliases: ['australia', 'sydney', 'melbourne'] },
  { code: 'IR', en: 'Iran', fa: 'ایران', flag: '🇮🇷', aliases: ['iran', 'tehran'] },
  { code: 'RO', en: 'Romania', fa: 'رومانی', flag: '🇷🇴', aliases: ['romania', 'bucharest'] },
  { code: 'BG', en: 'Bulgaria', fa: 'بلغارستان', flag: '🇧🇬', aliases: ['bulgaria', 'sofia'] },
  { code: 'MD', en: 'Moldova', fa: 'مولداوی', flag: '🇲🇩', aliases: ['moldova', 'chisinau'] },
]

const PROVIDERS: { key: string; label: string; aliases: string[] }[] = [
  { key: 'linode', label: 'Linode', aliases: ['linode', 'akamai', 'li'] },
  { key: 'hetzner', label: 'Hetzner', aliases: ['hetzner', 'hz'] },
  { key: 'ovh', label: 'OVH', aliases: ['ovh'] },
  { key: 'vultr', label: 'Vultr', aliases: ['vultr', 'vult'] },
  { key: 'digitalocean', label: 'DigitalOcean', aliases: ['digitalocean', 'digital ocean', 'docean'] },
  { key: 'contabo', label: 'Contabo', aliases: ['contabo'] },
  { key: 'aws', label: 'AWS', aliases: ['aws', 'amazon', 'ec2'] },
  { key: 'azure', label: 'Azure', aliases: ['azure'] },
  { key: 'gcp', label: 'GCP', aliases: ['gcp', 'googlecloud', 'google cloud'] },
  { key: 'oracle', label: 'Oracle', aliases: ['oracle', 'oci'] },
  { key: 'mivocloud', label: 'MivoCloud', aliases: ['mivo', 'mivocloud'] },
  { key: 'time4vps', label: 'Time4VPS', aliases: ['time4vps', 'time 4 vps'] },
  { key: 'linevps', label: 'LineVPS', aliases: ['linevps', 'line vps'] },
  { key: 'dataforest', label: 'DataForest', aliases: ['dataforest', 'data forest', 'df'] },
  { key: 'buyvm', label: 'BuyVM', aliases: ['buyvm', 'buy vm'] },
  { key: 'racknerd', label: 'RackNerd', aliases: ['racknerd', 'rack nerd'] },
  { key: 'hostinger', label: 'Hostinger', aliases: ['hostinger'] },
  { key: 'netcup', label: 'netcup', aliases: ['netcup'] },
  { key: 'scaleway', label: 'Scaleway', aliases: ['scaleway'] },
]

/** Short aliases that must match as whole tokens only (avoid "li" inside "public"). */
const TOKEN_ONLY_PROVIDER_ALIASES = new Set(['li', 'hz', 'df'])
const TOKEN_ONLY_COUNTRY_ALIASES = new Set(['sw', 'uk', 'ams', 'fra', 'hel', 'lon', 'par', 'sgp'])

const TZ_COUNTRY: Record<string, string> = {
  'Europe/Amsterdam': 'NL',
  'Europe/Berlin': 'DE',
  'Europe/Paris': 'FR',
  'Europe/London': 'GB',
  'Europe/Dublin': 'IE',
  'Europe/Madrid': 'ES',
  'Europe/Rome': 'IT',
  'Europe/Vienna': 'AT',
  'Europe/Zurich': 'CH',
  'Europe/Stockholm': 'SE',
  'Europe/Oslo': 'NO',
  'Europe/Helsinki': 'FI',
  'Europe/Warsaw': 'PL',
  'Europe/Prague': 'CZ',
  'Europe/Brussels': 'BE',
  'Europe/Lisbon': 'PT',
  'Europe/Istanbul': 'TR',
  'Europe/Moscow': 'RU',
  'Europe/Kyiv': 'UA',
  'Asia/Tehran': 'IR',
  'Asia/Dubai': 'AE',
  'Asia/Singapore': 'SG',
  'Asia/Tokyo': 'JP',
  'Asia/Seoul': 'KR',
  'Asia/Hong_Kong': 'HK',
  'Asia/Kolkata': 'IN',
  'America/New_York': 'US',
  'America/Los_Angeles': 'US',
  'America/Chicago': 'US',
  'America/Toronto': 'CA',
  'America/Sao_Paulo': 'BR',
  'Australia/Sydney': 'AU',
  'Iran Standard Time': 'IR',
  'W. Europe Standard Time': 'DE',
  'Central Europe Standard Time': 'PL',
  'Romance Standard Time': 'FR',
  'GMT Standard Time': 'GB',
  'Eastern Standard Time': 'US',
  'Pacific Standard Time': 'US',
  'Tokyo Standard Time': 'JP',
  'Singapore Standard Time': 'SG',
  'Arabic Standard Time': 'AE',
  'Turkey Standard Time': 'TR',
  'Russian Standard Time': 'RU',
}

const ISP_PROVIDER_HINTS: { label: string; needles: string[] }[] = [
  { label: 'Linode', needles: ['linode', 'akamai'] },
  { label: 'Hetzner', needles: ['hetzner'] },
  { label: 'OVH', needles: ['ovh'] },
  { label: 'Vultr', needles: ['vultr', 'choopa'] },
  { label: 'DigitalOcean', needles: ['digitalocean', 'digital ocean'] },
  { label: 'Contabo', needles: ['contabo'] },
  { label: 'AWS', needles: ['amazon', 'aws'] },
  { label: 'Azure', needles: ['microsoft', 'azure'] },
  { label: 'GCP', needles: ['google'] },
  { label: 'DataForest', needles: ['dataforest', 'data forest'] },
  { label: 'MivoCloud', needles: ['mivo'] },
  { label: 'netcup', needles: ['netcup'] },
]

const emptyLocation = (): InfraLocation => ({
  countryCode: null,
  countryEn: null,
  countryFa: null,
  flag: null,
  datacenter: null,
})

const normalizeText = (value: string) =>
  value
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, ' ')
    .replace(/\s+/g, ' ')
    .trim()

const normalizeHaystack = (...parts: Array<string | null | undefined>) =>
  normalizeText(parts.filter(Boolean).join(' '))

const tokensOf = (haystack: string) => haystack.split(' ').filter(Boolean)

export const countryFromCode = (code: string | null | undefined): InfraLocation => {
  if (!code) return emptyLocation()
  const meta = COUNTRIES.find(c => c.code === code.toUpperCase())
  if (!meta) return emptyLocation()
  return {
    countryCode: meta.code,
    countryEn: meta.en,
    countryFa: meta.fa,
    flag: meta.flag,
    datacenter: null,
  }
}

const aliasMatches = (haystack: string, tokens: string[], aliasRaw: string, tokenOnly: boolean) => {
  const alias = normalizeText(aliasRaw)
  if (!alias) return false
  if (tokenOnly || !alias.includes(' ') && alias.length <= 3) {
    return tokens.includes(alias)
  }
  return haystack.includes(alias)
}

const findCountry = (haystack: string): CountryMeta | null => {
  const tokens = tokensOf(haystack)

  for (const meta of COUNTRIES) {
    if (tokens.includes(meta.code.toLowerCase())) return meta
  }

  for (const meta of COUNTRIES) {
    for (const alias of meta.aliases) {
      if (aliasMatches(haystack, tokens, alias, TOKEN_ONLY_COUNTRY_ALIASES.has(alias))) return meta
    }
  }

  // Compound names without separators: DEVULT, NLLINODE, LINODEDE
  const compact = haystack.replace(/\s/g, '')
  if (compact.length >= 4) {
    for (const meta of COUNTRIES) {
      const code = meta.code.toLowerCase()
      if (compact.startsWith(code) && compact.length > code.length + 1) return meta
      if (compact.endsWith(code) && compact.length > code.length + 1) return meta
    }
  }

  return null
}

const findProvider = (haystack: string): string | null => {
  const tokens = tokensOf(haystack)

  for (const provider of PROVIDERS) {
    for (const alias of provider.aliases) {
      if (aliasMatches(haystack, tokens, alias, TOKEN_ONLY_PROVIDER_ALIASES.has(alias))) return provider.label
    }
  }

  const compact = haystack.replace(/\s/g, '')
  for (const provider of PROVIDERS) {
    for (const alias of provider.aliases) {
      const needle = normalizeText(alias).replace(/\s/g, '')
      if (needle.length >= 4 && compact.includes(needle)) return provider.label
    }
  }

  return null
}

const providerFromIsp = (isp?: string | null): string | null => {
  if (!isp) return null
  const hay = normalizeText(isp)
  for (const item of ISP_PROVIDER_HINTS) {
    if (item.needles.some(n => hay.includes(normalizeText(n)))) return item.label
  }
  // Fall back to shortened org name
  const clean = isp.split(/[|,]/)[0]?.trim()
  return clean && clean.length <= 28 ? clean : clean?.slice(0, 28) || null
}

/** Infer country / datacenter from node name, address, hostname, or timezone. */
export const resolveInfraLocation = (...parts: Array<string | null | undefined>): InfraLocation => {
  const haystack = normalizeHaystack(...parts)
  if (!haystack) return emptyLocation()

  const country = findCountry(haystack)
  const datacenter = findProvider(haystack)

  if (!country && !datacenter) return emptyLocation()

  return {
    countryCode: country?.code ?? null,
    countryEn: country?.en ?? null,
    countryFa: country?.fa ?? null,
    flag: country?.flag ?? null,
    datacenter,
  }
}

export const mergeInfraLocations = (...parts: Array<InfraLocation | null | undefined>): InfraLocation => {
  const result = emptyLocation()
  for (const part of parts) {
    if (!part) continue
    if (!result.countryCode && part.countryCode) {
      result.countryCode = part.countryCode
      result.countryEn = part.countryEn
      result.countryFa = part.countryFa
      result.flag = part.flag
    }
    if (!result.datacenter && part.datacenter) {
      result.datacenter = part.datacenter
    }
  }
  return result
}

export const resolveLocationFromTimezone = (timezone?: string | null): InfraLocation => {
  if (!timezone) return emptyLocation()
  const code = TZ_COUNTRY[timezone] || TZ_COUNTRY[timezone.replace(' ', '_')]
  return countryFromCode(code)
}

export const displayCountryName = (location: InfraLocation, locale?: string) => {
  const isFa = (locale || '').toLowerCase().startsWith('fa')
  return (isFa ? location.countryFa : location.countryEn) || location.countryEn || location.countryFa || null
}

export const isPublicIp = (value?: string | null): boolean => {
  if (!value) return false
  const host = value.trim().replace(/^\[|\]$/g, '')
  if (!/^\d{1,3}(?:\.\d{1,3}){3}$/.test(host)) return false
  const parts = host.split('.').map(Number)
  if (parts.some(n => Number.isNaN(n) || n < 0 || n > 255)) return false
  const [a, b] = parts
  if (a === 10 || a === 127 || a === 0) return false
  if (a === 192 && b === 168) return false
  if (a === 172 && b >= 16 && b <= 31) return false
  if (a === 169 && b === 254) return false
  return true
}

type IpWhoResponse = {
  success?: boolean
  country?: string
  country_code?: string
  connection?: { isp?: string; org?: string }
  org?: string
}

const geoCache = new Map<string, InfraLocation>()
const geoInflight = new Map<string, Promise<InfraLocation | null>>()

export const lookupIpGeo = async (ip?: string | null): Promise<InfraLocation | null> => {
  if (!isPublicIp(ip)) return null
  const key = ip!.trim()
  const cached = geoCache.get(key)
  if (cached) return cached

  const existing = geoInflight.get(key)
  if (existing) return existing

  const request = (async () => {
    try {
      const response = await fetch(`https://ipwho.is/${encodeURIComponent(key)}`)
      if (!response.ok) return null
      const data = (await response.json()) as IpWhoResponse
      if (!data?.success || !data.country_code) return null
      const base = countryFromCode(data.country_code)
      if (!base.countryCode) {
        base.countryEn = data.country || null
        base.countryCode = data.country_code.toUpperCase()
      }
      base.datacenter = providerFromIsp(data.connection?.isp || data.connection?.org || data.org)
      geoCache.set(key, base)
      return base
    } catch {
      return null
    } finally {
      geoInflight.delete(key)
    }
  })()

  geoInflight.set(key, request)
  return request
}
