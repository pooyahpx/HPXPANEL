import { z } from 'zod'

export const builtInVariableKeys = [
  'SERVER_IP',
  'SERVER_IPV6',
  'USERNAME',
  'DATA_USAGE',
  'DATA_LIMIT',
  'DATA_LEFT',
  'DAYS_LEFT',
  'EXPIRE_DATE',
  'JALALI_EXPIRE_DATE',
  'TIME_LEFT',
  'STATUS_EMOJI',
  'USAGE_PERCENTAGE',
  'ADMIN_USERNAME',
  'PROFILE_TITLE',
  'PROTOCOL',
  'TRANSPORT',
  'URL',
  'FORMAT',
] as const

export const customVariableSchema = z.object({
  key: z
    .string()
    .max(64, 'Variable key must be 64 characters or less')
    .regex(/^$|^[A-Z][A-Z0-9_]*$/, 'Use uppercase letters, numbers, and underscores')
    .default(''),
  value: z.string().max(512, 'Variable value must be 512 characters or less').default(''),
})

export const customVariablesSchema = z
  .array(customVariableSchema)
  .default([])
  .superRefine((variables, ctx) => {
    const seen = new Set<string>()
    for (const [index, variable] of variables.entries()) {
      if (!variable.key) continue
      if ((builtInVariableKeys as readonly string[]).includes(variable.key)) {
        ctx.addIssue({
          code: z.ZodIssueCode.custom,
          message: 'Custom variable conflicts with a built-in variable',
          path: [index, 'key'],
        })
      }
      if (seen.has(variable.key)) {
        ctx.addIssue({
          code: z.ZodIssueCode.custom,
          message: 'Duplicate custom variable',
          path: [index, 'key'],
        })
      }
      seen.add(variable.key)
    }
  })

export const normalizeCustomVariablesForPayload = (variables?: { key?: string; value?: string }[] | null) =>
  (variables || [])
    .map(variable => ({
      key: variable.key?.trim() || '',
      value: variable.value?.trim() || '',
    }))
    .filter(variable => variable.key)

export const subscriptionApplicationSchema = z.object({
  name: z.string().min(1, 'Application name is required').max(32, 'Application name must be 32 characters or less'),
  icon_url: z.string().url('Please enter a valid URL').optional().or(z.literal('')),
  import_url: z
    .string()
    .refine(
      url => {
        if (!url || url === '') return true
        return url.includes('{url}')
      },
      {
        message: 'Import URL must contain {url} placeholder for URL replacement',
      },
    )
    .optional()
    .or(z.literal('')),
  description: z.record(z.string()).optional(),
  recommended: z.boolean().optional(),
  show_when_hwid_enabled: z.boolean().optional(),
  platform: z.enum(['android', 'ios', 'windows', 'macos', 'linux', 'appletv', 'androidtv']),
  download_links: z
    .array(
      z.object({
        name: z.string().min(1, 'Download link name is required').max(64, 'Download link name must be 64 characters or less'),
        url: z.string().url('Please enter a valid URL'),
        language: z.enum(['fa', 'en', 'ru', 'zh']),
      }),
    )
    .min(1, 'At least one download link is required'),
})

export type SubscriptionApplicationFormData = z.infer<typeof subscriptionApplicationSchema>

export const externalConfigSchema = z.object({
  name: z.string().max(64, 'Name must be 64 characters or less').default(''),
  link: z
    .string()
    .min(8, 'Share link is required')
    .max(8192, 'Share link is too long')
    .refine(
      value => {
        const lowered = value.trim().toLowerCase()
        return (
          lowered.startsWith('vless://') ||
          lowered.startsWith('vmess://') ||
          lowered.startsWith('trojan://') ||
          lowered.startsWith('ss://') ||
          lowered.startsWith('ssr://') ||
          lowered.startsWith('hysteria://') ||
          lowered.startsWith('hysteria2://') ||
          lowered.startsWith('hy2://') ||
          lowered.startsWith('tuic://') ||
          lowered.startsWith('wireguard://') ||
          lowered.startsWith('wg://') ||
          lowered.startsWith('anytls://') ||
          lowered.startsWith('socks://') ||
          lowered.startsWith('socks5://') ||
          lowered.startsWith('http://') ||
          lowered.startsWith('https://')
        )
      },
      { message: 'Must be a share link (vless://, vmess://, trojan://, …)' },
    ),
  enabled: z.boolean().default(true),
  respect_user_quota: z.boolean().default(true),
})

export const subscriptionSchema = z.object({
  url_prefix: z.string().optional(),
  update_interval: z.number().min(1, 'Update interval must be at least 1 hour').max(168, 'Update interval cannot exceed 168 hours (1 week)').optional(),
  support_url: z.string().url('Please enter a valid URL').optional().or(z.literal('')),
  profile_title: z.string().optional(),
  announce: z.string().max(128, 'Announcement must be 128 characters or less').optional(),
  announce_url: z.string().url('Please enter a valid URL').optional().or(z.literal('')),
  allow_browser_config: z.boolean().optional(),
  disable_sub_template: z.boolean().optional(),
  randomize_order: z.boolean().optional(),
  custom_variables: customVariablesSchema,
  external_configs: z.array(externalConfigSchema).max(50).default([]),
  response_headers: z.record(z.string()).optional(),
  rules: z.array(
    z.object({
      pattern: z.string().min(1, 'Pattern is required'),
      target: z.enum(['links', 'links_base64', 'xray', 'wireguard', 'openvpn', 'sing_box', 'clash', 'clash_meta', 'outline', 'block']),
      response_headers: z.record(z.string()).optional(),
    }),
  ),
  applications: z.array(subscriptionApplicationSchema).optional(),
  manual_sub_request: z
    .object({
      links: z.boolean().optional(),
      links_base64: z.boolean().optional(),
      xray: z.boolean().optional(),
      wireguard: z.boolean().optional(),
      openvpn: z.boolean().optional(),
      sing_box: z.boolean().optional(),
      clash: z.boolean().optional(),
      clash_meta: z.boolean().optional(),
      outline: z.boolean().optional(),
    })
    .optional(),
})

export type SubscriptionFormData = z.infer<typeof subscriptionSchema>
export type SubscriptionRuleFormData = SubscriptionFormData['rules'][number]
export type SubscriptionPlatform = SubscriptionApplicationFormData['platform']
export type SubscriptionLanguage = NonNullable<SubscriptionApplicationFormData['download_links']>[number]['language']

export const defaultSubscriptionRules: SubscriptionRuleFormData[] = [
  {
    pattern: '^([Cc]lash[\\-\\.]?[Vv]erge|[Cc]lash[\\-\\.]?[Mm]eta|[Ff][Ll][Cc]lash|[Mm]ihomo)',
    target: 'clash_meta',
  },
  {
    pattern: '^([Cc]lash|[Ss]tash)',
    target: 'clash',
  },
  {
    pattern: '^(SFA|SFI|SFM|SFT|[Kk]aring|[Hh]iddify[Nn]ext)|.*[Ss]ing[\\-b]?ox.*',
    target: 'sing_box',
  },
  {
    pattern: '^(SS|SSR|SSD|SSS|Outline|Shadowsocks|SSconf)',
    target: 'outline',
  },
  {
    pattern: '^([Vv]2rayNG|[Vv]2rayN|[Ss]treisand|[Hh]app|[Kk]tor\\-client)',
    target: 'xray',
  },
  {
    pattern: '.*',
    target: 'links_base64',
  },
]
