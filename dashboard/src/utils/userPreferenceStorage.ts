/** List vs grid for {@link CoreEditorDataTable} sections (inbounds, outbounds, routing, …). */
export type CoreEditorViewMode = 'list' | 'grid'

export const CORE_EDITOR_VIEW_MODE_STORAGE_KEY = 'view-mode:core-editor-lists'

export const DEFAULT_CORE_EDITOR_VIEW_MODE: CoreEditorViewMode = 'list'

const NUM_USERS_PER_PAGE_LOCAL_STORAGE_KEY = 'hpxpanel-num-users-per-page'
const NUM_ADMINS_PER_PAGE_LOCAL_STORAGE_KEY = 'hpxpanel-num-admins-per-page'
const NUM_ITEMS_PER_PAGE_DEFAULT = 10

const USERS_AUTO_REFRESH_INTERVAL_KEY = 'hpxpanel-users-auto-refresh-interval'
const DEFAULT_USERS_AUTO_REFRESH_INTERVAL_SECONDS = 15
const USERS_SHOW_CREATED_BY_KEY = 'hpxpanel-users-show-created-by'
const DEFAULT_USERS_SHOW_CREATED_BY = true
const USERS_SHOW_SELECTION_CHECKBOX_KEY = 'hpxpanel-users-show-selection-checkbox'
const DEFAULT_USERS_SHOW_SELECTION_CHECKBOX = true
const CHART_VIEW_TYPE_KEY = 'hpxpanel-chart-view-type'

const CORES_LIST_USE_CONFIG_MODAL_KEY = 'hpxpanel-cores-list-use-config-modal'
const DEFAULT_CORES_LIST_USE_CONFIG_MODAL = false

export const DATE_PICKER_PREFERENCE_KEY = 'hpxpanel-date-picker-preference'
export type DatePickerPreference = 'locale' | 'gregorian' | 'persian'
const DEFAULT_DATE_PICKER_PREFERENCE: DatePickerPreference = 'locale'

export const CHART_VIEW_TYPE_CHANGE_EVENT = 'hpxpanel-chart-view-type-change'
export type ChartViewType = 'bar' | 'area'
const DEFAULT_CHART_VIEW_TYPE: ChartViewType = 'bar'

// Generic function for any table type
export const getItemsPerPageLimitSize = (tableType: 'users' | 'admins' = 'users') => {
  const storageKey = tableType === 'users' ? NUM_USERS_PER_PAGE_LOCAL_STORAGE_KEY : NUM_ADMINS_PER_PAGE_LOCAL_STORAGE_KEY
  const numItemsPerPage = (typeof localStorage !== 'undefined' && localStorage.getItem(storageKey)) || NUM_ITEMS_PER_PAGE_DEFAULT.toString() // this catches `null` values
  return parseInt(numItemsPerPage) || NUM_ITEMS_PER_PAGE_DEFAULT // this catches NaN values
}

export const setItemsPerPageLimitSize = (value: string, tableType: 'users' | 'admins' = 'users') => {
  const storageKey = tableType === 'users' ? NUM_USERS_PER_PAGE_LOCAL_STORAGE_KEY : NUM_ADMINS_PER_PAGE_LOCAL_STORAGE_KEY
  return typeof localStorage !== 'undefined' && localStorage.setItem(storageKey, value)
}

// Legacy functions for backward compatibility
export const getUsersPerPageLimitSize = () => getItemsPerPageLimitSize('users')
export const setUsersPerPageLimitSize = (value: string) => setItemsPerPageLimitSize(value, 'users')

export const getAdminsPerPageLimitSize = () => getItemsPerPageLimitSize('admins')
export const setAdminsPerPageLimitSize = (value: string) => setItemsPerPageLimitSize(value, 'admins')

export const getUsersAutoRefreshIntervalSeconds = () => {
  const storedValue = typeof localStorage !== 'undefined' && localStorage.getItem(USERS_AUTO_REFRESH_INTERVAL_KEY)
  const parsed = storedValue ? parseInt(storedValue, 10) : DEFAULT_USERS_AUTO_REFRESH_INTERVAL_SECONDS
  return Number.isNaN(parsed) ? DEFAULT_USERS_AUTO_REFRESH_INTERVAL_SECONDS : parsed
}

export const setUsersAutoRefreshIntervalSeconds = (seconds: number) => {
  if (typeof localStorage === 'undefined') return
  localStorage.setItem(USERS_AUTO_REFRESH_INTERVAL_KEY, seconds.toString())
}

export const getUsersShowCreatedBy = () => {
  if (typeof localStorage === 'undefined') return DEFAULT_USERS_SHOW_CREATED_BY
  const storedValue = localStorage.getItem(USERS_SHOW_CREATED_BY_KEY)
  if (storedValue === null) return DEFAULT_USERS_SHOW_CREATED_BY
  return storedValue === 'true'
}

export const setUsersShowCreatedBy = (value: boolean) => {
  if (typeof localStorage === 'undefined') return
  localStorage.setItem(USERS_SHOW_CREATED_BY_KEY, value ? 'true' : 'false')
}

export const getUsersShowSelectionCheckbox = () => {
  if (typeof localStorage === 'undefined') return DEFAULT_USERS_SHOW_SELECTION_CHECKBOX
  const storedValue = localStorage.getItem(USERS_SHOW_SELECTION_CHECKBOX_KEY)
  if (storedValue === null) return DEFAULT_USERS_SHOW_SELECTION_CHECKBOX
  return storedValue === 'true'
}

export const setUsersShowSelectionCheckbox = (value: boolean) => {
  if (typeof localStorage === 'undefined') return
  localStorage.setItem(USERS_SHOW_SELECTION_CHECKBOX_KEY, value ? 'true' : 'false')
}

export const getDatePickerPreference = (): DatePickerPreference => {
  if (typeof localStorage === 'undefined') return DEFAULT_DATE_PICKER_PREFERENCE
  const storedValue = localStorage.getItem(DATE_PICKER_PREFERENCE_KEY)
  if (storedValue === 'locale' || storedValue === 'gregorian' || storedValue === 'persian') {
    return storedValue
  }
  return DEFAULT_DATE_PICKER_PREFERENCE
}

export const setDatePickerPreference = (preference: DatePickerPreference) => {
  if (typeof localStorage === 'undefined') return
  localStorage.setItem(DATE_PICKER_PREFERENCE_KEY, preference)
}

export const getChartViewTypePreference = (): ChartViewType => {
  if (typeof localStorage === 'undefined') return DEFAULT_CHART_VIEW_TYPE
  const storedValue = localStorage.getItem(CHART_VIEW_TYPE_KEY)
  if (storedValue === 'bar' || storedValue === 'area') {
    return storedValue
  }
  return DEFAULT_CHART_VIEW_TYPE
}

export const setChartViewTypePreference = (viewType: ChartViewType) => {
  if (typeof localStorage === 'undefined') return
  localStorage.setItem(CHART_VIEW_TYPE_KEY, viewType)
  if (typeof window !== 'undefined') {
    window.dispatchEvent(new CustomEvent<ChartViewType>(CHART_VIEW_TYPE_CHANGE_EVENT, { detail: viewType }))
  }
}

export const getCoresListUseConfigModal = (): boolean => {
  if (typeof localStorage === 'undefined') return DEFAULT_CORES_LIST_USE_CONFIG_MODAL
  return localStorage.getItem(CORES_LIST_USE_CONFIG_MODAL_KEY) === 'true'
}

export const setCoresListUseConfigModal = (value: boolean) => {
  if (typeof localStorage === 'undefined') return
  localStorage.setItem(CORES_LIST_USE_CONFIG_MODAL_KEY, value ? 'true' : 'false')
}

/** UI density · font scale · motion · mesh — applied on <html> */
export type UiDensity = 'compact' | 'comfortable' | 'spacious'
export type FontScale = 'sm' | 'md' | 'lg'

const UI_DENSITY_KEY = 'hpxpanel-ui-density'
const FONT_SCALE_KEY = 'hpxpanel-font-scale'
const REDUCED_MOTION_KEY = 'hpxpanel-reduced-motion'
const MESH_BG_KEY = 'hpxpanel-mesh-bg'

const DEFAULT_UI_DENSITY: UiDensity = 'comfortable'
const DEFAULT_FONT_SCALE: FontScale = 'md'
const DEFAULT_REDUCED_MOTION = false
const DEFAULT_MESH_BG = true

export const UI_PREFS_CHANGE_EVENT = 'hpxpanel-ui-prefs-change'

function applyHtmlUiPrefs(partial?: {
  density?: UiDensity
  fontScale?: FontScale
  reducedMotion?: boolean
  meshBg?: boolean
}) {
  if (typeof document === 'undefined') return
  const root = document.documentElement
  const density = partial?.density ?? getUiDensity()
  const fontScale = partial?.fontScale ?? getFontScale()
  const reducedMotion = partial?.reducedMotion ?? getReducedMotion()
  const meshBg = partial?.meshBg ?? getMeshBackground()
  root.dataset.density = density
  root.dataset.fontScale = fontScale
  root.dataset.reducedMotion = reducedMotion ? 'true' : 'false'
  root.dataset.meshBg = meshBg ? 'on' : 'off'
  if (typeof window !== 'undefined') {
    window.dispatchEvent(new CustomEvent(UI_PREFS_CHANGE_EVENT))
  }
}

export const getUiDensity = (): UiDensity => {
  if (typeof localStorage === 'undefined') return DEFAULT_UI_DENSITY
  const v = localStorage.getItem(UI_DENSITY_KEY)
  if (v === 'compact' || v === 'comfortable' || v === 'spacious') return v
  return DEFAULT_UI_DENSITY
}

export const setUiDensity = (value: UiDensity) => {
  if (typeof localStorage === 'undefined') return
  localStorage.setItem(UI_DENSITY_KEY, value)
  applyHtmlUiPrefs({ density: value })
}

export const getFontScale = (): FontScale => {
  if (typeof localStorage === 'undefined') return DEFAULT_FONT_SCALE
  const v = localStorage.getItem(FONT_SCALE_KEY)
  if (v === 'sm' || v === 'md' || v === 'lg') return v
  return DEFAULT_FONT_SCALE
}

export const setFontScale = (value: FontScale) => {
  if (typeof localStorage === 'undefined') return
  localStorage.setItem(FONT_SCALE_KEY, value)
  applyHtmlUiPrefs({ fontScale: value })
}

export const getReducedMotion = (): boolean => {
  if (typeof localStorage === 'undefined') return DEFAULT_REDUCED_MOTION
  return localStorage.getItem(REDUCED_MOTION_KEY) === 'true'
}

export const setReducedMotion = (value: boolean) => {
  if (typeof localStorage === 'undefined') return
  localStorage.setItem(REDUCED_MOTION_KEY, value ? 'true' : 'false')
  applyHtmlUiPrefs({ reducedMotion: value })
}

export const getMeshBackground = (): boolean => {
  if (typeof localStorage === 'undefined') return DEFAULT_MESH_BG
  const v = localStorage.getItem(MESH_BG_KEY)
  if (v === null) return DEFAULT_MESH_BG
  return v !== 'false'
}

export const setMeshBackground = (value: boolean) => {
  if (typeof localStorage === 'undefined') return
  localStorage.setItem(MESH_BG_KEY, value ? 'true' : 'false')
  applyHtmlUiPrefs({ meshBg: value })
}

export const resetUiAppearancePrefs = () => {
  if (typeof localStorage === 'undefined') return
  localStorage.setItem(UI_DENSITY_KEY, DEFAULT_UI_DENSITY)
  localStorage.setItem(FONT_SCALE_KEY, DEFAULT_FONT_SCALE)
  localStorage.setItem(REDUCED_MOTION_KEY, 'false')
  localStorage.setItem(MESH_BG_KEY, 'true')
  applyHtmlUiPrefs({
    density: DEFAULT_UI_DENSITY,
    fontScale: DEFAULT_FONT_SCALE,
    reducedMotion: false,
    meshBg: true,
  })
}

/** Call once on app boot */
export const hydrateUiAppearancePrefs = () => {
  applyHtmlUiPrefs()
}
