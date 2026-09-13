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
  { code: 'CH', en: 'Switzerland', fa: 'سوئیس', flag: '🇨🇭', aliases: ['switzerland', 'zurich'] },
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
  { code: 'HK', en: 'Hong Kong', fa: 'هنگ‌کنگ', flag: '🇭🇰', aliases: ['hongkong', 'hk'] },
  { code: 'IN', en: 'India', fa: 'هند', flag: '🇮🇳', aliases: ['india', 'mumbai', 'delhi'] },
  { code: 'CA', en: 'Canada', fa: 'کانادا', flag: '🇨🇦', aliases: ['canada', 'toronto', 'montreal'] },
  { code: 'BR', en: 'Brazil', fa: 'برزیل', flag: '🇧🇷', aliases: ['brazil', 'sao', 'saopaulo'] },
  { code: 'AU', en: 'Australia', fa: 'استرالیا', flag: '🇦🇺', aliases: ['australia', 'sydney', 'melbourne'] },
  { code: 'IR', en: 'Iran', fa: 'ایران', flag: '🇮🇷', aliases: ['iran', 'tehran'] },
]

const PROVIDERS: { key: string; label: string; aliases: string[] }[] = [
  { key: 'linode', label: 'Linode', aliases: ['linode', 'akamai'] },
  { key: 'hetzner', label: 'Hetzner', aliases: ['hetzner', 'hz'] },
  { key: 'ovh', label: 'OVH', aliases: ['ovh'] },
  { key: 'vultr', label: 'Vultr', aliases: ['vultr'] },
  { key: 'digitalocean', label: 'DigitalOcean', aliases: ['digitalocean', 'digital-ocean', 'docean'] },
  { key: 'contabo', label: 'Contabo', aliases: ['contabo'] },
  { key: 'aws', label: 'AWS', aliases: ['aws', 'amazon', 'ec2'] },
  { key: 'azure', label: 'Azure', aliases: ['azure'] },
  { key: 'gcp', label: 'GCP', aliases: ['gcp', 'googlecloud'] },
  { key: 'oracle', label: 'Oracle', aliases: ['oracle', 'oci'] },
  { key: 'mivocloud', label: 'MivoCloud', aliases: ['mivo', 'mivocloud'] },
  { key: 'time4vps', label: 'Time4VPS', aliases: ['time4vps'] },
  { key: 'linevps', label: 'LineVPS', aliases: ['linevps'] },
  { key: 'dataforest', label: 'DataForest', aliases: ['dataforest', 'data-forest', 'data_forest'] },
  { key: 'buyvm', label: 'BuyVM', aliases: ['buyvm'] },
  { key: 'racknerd', label: 'RackNerd', aliases: ['racknerd'] },
  { key: 'hostinger', label: 'Hostinger', aliases: ['hostinger'] },
]

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
  // Windows timezone display names
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

const emptyLocation = (): InfraLocation => ({
  countryCode: null,
  countryEn: null,
  countryFa: null,
  flag: null,
  datacenter: null,
})

const normalizeHaystack = (...parts: Array<string | null | undefined>) =>
  parts
    .filter(Boolean)
    .join(' ')
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, ' ')
    .replace(/\s+/g, ' ')
    .trim()

const countryFromCode = (code: string | null | undefined): InfraLocation => {
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

const findCountry = (haystack: string): CountryMeta | null => {
  // Prefer ISO-style tokens: DE, NL, FR as standalone words
  for (const meta of COUNTRIES) {
    const codeRe = new RegExp(`(?:^|\\s)${meta.code.toLowerCase()}(?:\\s|$)`)
    if (codeRe.test(haystack)) return meta
  }
  for (const meta of COUNTRIES) {
    for (const alias of meta.aliases) {
      if (haystack.includes(alias)) return meta
    }
  }
  return null
}

const findProvider = (haystack: string): string | null => {
  for (const provider of PROVIDERS) {
    for (const alias of provider.aliases) {
      if (haystack.includes(alias)) return provider.label
    }
  }
  return null
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

export const resolveLocationFromTimezone = (timezone?: string | null): InfraLocation => {
  if (!timezone) return emptyLocation()
  const code = TZ_COUNTRY[timezone] || TZ_COUNTRY[timezone.replace(' ', '_')]
  return countryFromCode(code)
}

export const displayCountryName = (location: InfraLocation, locale?: string) => {
  const isFa = (locale || '').toLowerCase().startsWith('fa')
  return (isFa ? location.countryFa : location.countryEn) || location.countryEn || location.countryFa || null
}
