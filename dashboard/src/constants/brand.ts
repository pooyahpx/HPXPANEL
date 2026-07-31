import { joinURL } from 'ufo'

/** HPX brand mark — resolves under dashboard BASE_URL (e.g. /dashboard/). */
export const HPX_LOGO_URL = joinURL(import.meta.env.BASE_URL || '/', 'statics/brand/hpx-logo.png')
export const HPX_LOGO_SVG_URL = joinURL(import.meta.env.BASE_URL || '/', 'statics/brand/hpx-logo.svg')
