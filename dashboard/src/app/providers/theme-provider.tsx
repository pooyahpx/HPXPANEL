import { createContext, useContext, useEffect, useState, useCallback, useMemo } from 'react'

export type Theme = 'dark' | 'light' | 'system'
export type ColorTheme = 'default' | 'red' | 'rose' | 'orange' | 'green' | 'blue' | 'yellow' | 'violet'
export type Radius = '0' | '0.3rem' | '0.5rem' | '0.75rem' | '1rem'

type ThemeProviderProps = {
  children: React.ReactNode
  defaultTheme?: Theme
  defaultColorTheme?: ColorTheme
  defaultRadius?: Radius
  storageKey?: string
  colorStorageKey?: string
  radiusStorageKey?: string
}

type ThemeProviderState = {
  theme: Theme
  colorTheme: ColorTheme
  radius: Radius
  resolvedTheme: 'light' | 'dark'
  setTheme: (theme: Theme) => void
  setColorTheme: (colorTheme: ColorTheme) => void
  setRadius: (radius: Radius) => void
  resetToDefaults: () => void
  isSystemTheme: boolean
}

// Color theme definitions with proper typing
const colorThemes: Record<
  ColorTheme,
  {
    name: string
    light: Record<string, string>
    dark: Record<string, string>
  }
> = {
  default: {
    name: 'Readable Pixel',
    light: {
      '--background': '220 25% 97%',
      '--foreground': '222 47% 11%',
      '--primary': '224 76% 52%',
      '--primary-foreground': '0 0% 100%',
      '--secondary': '220 20% 92%',
      '--secondary-foreground': '222 47% 14%',
      '--muted': '220 18% 91%',
      '--muted-foreground': '215 20% 36%',
      '--accent': '221 70% 92%',
      '--accent-foreground': '224 65% 28%',
      '--destructive': '0 72% 51%',
      '--destructive-foreground': '0 0% 100%',
      '--border': '218 18% 68%',
      '--input': '0 0% 100%',
      '--ring': '224 76% 52%',
      '--card': '0 0% 100%',
      '--card-foreground': 'var(--foreground)',
      '--popover': '0 0% 100%',
      '--popover-foreground': 'var(--foreground)',
      '--sidebar-background': '222 40% 10%',
      '--sidebar-foreground': '214 32% 94%',
      '--sidebar-primary': '220 86% 62%',
      '--sidebar-primary-foreground': '222 47% 10%',
      '--sidebar-accent': '222 30% 17%',
      '--sidebar-accent-foreground': '214 32% 96%',
      '--sidebar-border': '220 24% 24%',
      '--sidebar-ring': '220 86% 62%',
      '--chart-1': '224 76% 52%',
      '--chart-2': '0 72% 51%',
      '--chart-3': '38 92% 50%',
      '--chart-4': '152 55% 40%',
      '--chart-5': '280 40% 48%',
      '--mesh-a': '220 80% 91%',
      '--mesh-b': '245 60% 94%',
      '--mesh-c': '190 55% 93%',
      '--surface-glow': '224 76% 58%',
      '--hover-primary': '224 76% 44%',
      '--hover-secondary': '220 18% 85%',
      '--hover-destructive': '0 72% 43%',
      '--pixel-border': '222 35% 20%',
    },
    dark: {
      '--background': '222 47% 7%',
      '--foreground': '214 32% 94%',
      '--primary': '220 86% 64%',
      '--primary-foreground': '222 47% 9%',
      '--secondary': '222 25% 18%',
      '--secondary-foreground': '214 32% 94%',
      '--muted': '222 28% 15%',
      '--muted-foreground': '215 20% 70%',
      '--accent': '222 32% 20%',
      '--accent-foreground': '214 40% 96%',
      '--destructive': '0 72% 58%',
      '--destructive-foreground': '0 0% 100%',
      '--border': '220 20% 32%',
      '--input': '222 30% 14%',
      '--ring': '220 86% 64%',
      '--card': '222 38% 10%',
      '--card-foreground': 'var(--foreground)',
      '--popover': '222 38% 10%',
      '--popover-foreground': 'var(--foreground)',
      '--sidebar-background': '224 50% 6%',
      '--sidebar-foreground': '214 32% 94%',
      '--sidebar-primary': '220 86% 66%',
      '--sidebar-primary-foreground': '222 47% 9%',
      '--sidebar-accent': '222 32% 16%',
      '--sidebar-accent-foreground': '214 40% 96%',
      '--sidebar-border': '220 24% 20%',
      '--sidebar-ring': '220 86% 66%',
      '--chart-1': '220 86% 64%',
      '--chart-2': '0 72% 58%',
      '--chart-3': '38 92% 58%',
      '--chart-4': '152 60% 48%',
      '--chart-5': '280 50% 62%',
      '--mesh-a': '224 45% 15%',
      '--mesh-b': '245 35% 13%',
      '--mesh-c': '190 30% 12%',
      '--surface-glow': '220 70% 48%',
      '--hover-primary': '220 86% 72%',
      '--hover-secondary': '222 24% 24%',
      '--hover-destructive': '0 72% 50%',
      '--pixel-border': '215 24% 58%',
    },
  },
  red: {
    name: 'Red',
    light: {
      '--background': '240 5% 96%',
      '--foreground': '240 5% 10%',
      '--primary': '0 72.2% 50.6%',
      '--primary-foreground': '0 85.7% 97.3%',
      '--secondary': '0 0% 96.1%',
      '--secondary-foreground': '0 0% 9%',
      '--muted': '240 5% 90%',
      '--muted-foreground': '240 5% 40%',
      '--accent': '240 5% 90%',
      '--accent-foreground': '0 0% 9%',
      '--destructive': '0 72% 51%',
      '--destructive-foreground': '0 0% 98%',
      '--border': '240 5% 80%',
      '--input': '240 6% 91%',
      '--ring': '0 72.2% 50.6%',
      '--card': '240 5% 98%',
      '--card-foreground': 'var(--foreground)',
      '--popover': 'var(--background)',
      '--popover-foreground': 'var(--foreground)',
      '--chart-1': '0 72.2% 50.6%',
      '--chart-2': '15 100% 50%',
      '--chart-3': '30 100% 50%',
      '--chart-4': '45 100% 50%',
      '--chart-5': '60 100% 50%',
    },
    dark: {
      '--background': '240 2% 11%',
      '--foreground': '0 0% 98%',
      '--primary': '0 72.2% 50.6%',
      '--primary-foreground': '0 85.7% 97.3%',
      '--secondary': '0 0% 14.9%',
      '--secondary-foreground': '0 0% 98%',
      '--muted': '0 0% 14.9%',
      '--muted-foreground': '0 0% 63.9%',
      '--accent': '0 0% 14.9%',
      '--accent-foreground': '0 0% 98%',
      '--destructive': '0 72% 51%',
      '--destructive-foreground': '210 40% 98%',
      '--border': '0 0% 18%',
      '--input': '240 2% 16.5%',
      '--ring': '215 16% 47%',
      '--card': '240 2% 11.5%',
      '--card-foreground': 'var(--foreground)',
      '--popover': 'var(--background)',
      '--popover-foreground': 'var(--foreground)',
      '--chart-1': '0 72.2% 50.6%',
      '--chart-2': '15 100% 60%',
      '--chart-3': '30 100% 60%',
      '--chart-4': '45 100% 60%',
      '--chart-5': '60 100% 60%',
    },
  },
  rose: {
    name: 'Rose',
    light: {
      '--background': '240 5% 96%',
      '--foreground': '240 5% 10%',
      '--primary': '346.8 77.2% 49.8%',
      '--primary-foreground': '355.7 100% 97.3%',
      '--secondary': '240 4.8% 95.9%',
      '--secondary-foreground': '240 5.9% 10%',
      '--muted': '240 5% 90%',
      '--muted-foreground': '240 5% 40%',
      '--accent': '240 5% 90%',
      '--accent-foreground': '240 5.9% 10%',
      '--destructive': '0 72% 51%',
      '--destructive-foreground': '0 0% 98%',
      '--border': '240 5% 80%',
      '--input': '240 6% 91%',
      '--ring': '346.8 77.2% 49.8%',
      '--card': '240 5% 98%',
      '--card-foreground': 'var(--foreground)',
      '--popover': 'var(--background)',
      '--popover-foreground': 'var(--foreground)',
      '--chart-1': '346.8 77.2% 49.8%',
      '--chart-2': '330 100% 50%',
      '--chart-3': '315 100% 50%',
      '--chart-4': '300 100% 50%',
      '--chart-5': '285 100% 50%',
    },
    dark: {
      '--background': '240 2% 11%',
      '--foreground': '0 0% 95%',
      '--primary': '346.8 77.2% 49.8%',
      '--primary-foreground': '355.7 100% 97.3%',
      '--secondary': '240 3.7% 15.9%',
      '--secondary-foreground': '0 0% 98%',
      '--muted': '0 0% 15%',
      '--muted-foreground': '0 0% 63.9%',
      '--accent': '12 6.5% 15.1%',
      '--accent-foreground': '0 0% 98%',
      '--destructive': '0 72% 51%',
      '--destructive-foreground': '210 40% 98%',
      '--border': '0 0% 18%',
      '--input': '240 2% 16.5%',
      '--ring': '215 16% 47%',
      '--card': '240 2% 11.5%',
      '--card-foreground': 'var(--foreground)',
      '--popover': 'var(--background)',
      '--popover-foreground': 'var(--foreground)',
      '--chart-1': '346.8 77.2% 49.8%',
      '--chart-2': '330 100% 60%',
      '--chart-3': '315 100% 60%',
      '--chart-4': '300 100% 60%',
      '--chart-5': '285 100% 60%',
    },
  },
  orange: {
    name: 'Orange',
    light: {
      '--background': '240 5% 96%',
      '--foreground': '240 5% 10%',
      '--primary': '24.6 95% 53.1%',
      '--primary-foreground': '60 9.1% 97.8%',
      '--secondary': '60 4.8% 95.9%',
      '--secondary-foreground': '24 9.8% 10%',
      '--muted': '240 5% 90%',
      '--muted-foreground': '240 5% 40%',
      '--accent': '240 5% 90%',
      '--accent-foreground': '24 9.8% 10%',
      '--destructive': '0 84.2% 60.2%',
      '--destructive-foreground': '60 9.1% 97.8%',
      '--border': '240 5% 80%',
      '--input': '240 6% 91%',
      '--ring': '24.6 95% 53.1%',
      '--card': '240 5% 98%',
      '--card-foreground': 'var(--foreground)',
      '--popover': 'var(--background)',
      '--popover-foreground': 'var(--foreground)',
      '--chart-1': '24.6 95% 53.1%',
      '--chart-2': '15 100% 50%',
      '--chart-3': '35 100% 50%',
      '--chart-4': '45 100% 50%',
      '--chart-5': '60 100% 50%',
    },
    dark: {
      '--background': '240 2% 11%',
      '--foreground': '60 9.1% 97.8%',
      '--primary': '20.5 90.2% 48.2%',
      '--primary-foreground': '60 9.1% 97.8%',
      '--secondary': '12 6.5% 15.1%',
      '--secondary-foreground': '60 9.1% 97.8%',
      '--muted': '12 6.5% 15.1%',
      '--muted-foreground': '0 0% 63.9%',
      '--accent': '12 6.5% 15.1%',
      '--accent-foreground': '60 9.1% 97.8%',
      '--destructive': '0 72% 51%',
      '--destructive-foreground': '60 9.1% 97.8%',
      '--border': '0 0% 18%',
      '--input': '240 2% 16.5%',
      '--ring': '215 16% 47%',
      '--card': '240 2% 11.5%',
      '--card-foreground': 'var(--foreground)',
      '--popover': 'var(--background)',
      '--popover-foreground': 'var(--foreground)',
      '--chart-1': '20.5 90.2% 48.2%',
      '--chart-2': '15 100% 60%',
      '--chart-3': '35 100% 60%',
      '--chart-4': '45 100% 60%',
      '--chart-5': '60 100% 60%',
    },
  },
  green: {
    name: 'Green',
    light: {
      '--background': '155 28% 97%',
      '--foreground': '168 42% 9%',
      '--primary': '152 72% 32%',
      '--primary-foreground': '0 0% 100%',
      '--secondary': '152 22% 90%',
      '--secondary-foreground': '168 30% 16%',
      '--muted': '152 18% 92%',
      '--muted-foreground': '165 12% 38%',
      '--accent': '152 30% 90%',
      '--accent-foreground': '168 30% 16%',
      '--destructive': '4 78% 48%',
      '--destructive-foreground': '0 0% 100%',
      '--border': '155 16% 84%',
      '--input': '152 20% 94%',
      '--ring': '152 72% 32%',
      '--card': '0 0% 100%',
      '--card-foreground': 'var(--foreground)',
      '--popover': '0 0% 100%',
      '--popover-foreground': 'var(--foreground)',
      '--sidebar-background': '170 40% 7%',
      '--sidebar-foreground': '150 20% 90%',
      '--sidebar-primary': '152 72% 44%',
      '--sidebar-primary-foreground': '170 40% 6%',
      '--sidebar-accent': '168 28% 14%',
      '--sidebar-accent-foreground': '150 25% 96%',
      '--sidebar-border': '168 22% 16%',
      '--sidebar-ring': '152 72% 44%',
      '--chart-1': '152 72% 36%',
      '--chart-2': '42 94% 52%',
      '--chart-3': '188 70% 40%',
      '--chart-4': '12 78% 52%',
      '--chart-5': '280 45% 48%',
    },
    dark: {
      '--background': '170 32% 5%',
      '--foreground': '150 20% 96%',
      '--primary': '152 78% 46%',
      '--primary-foreground': '170 40% 6%',
      '--secondary': '168 22% 14%',
      '--secondary-foreground': '150 20% 92%',
      '--muted': '168 22% 12%',
      '--muted-foreground': '150 10% 62%',
      '--accent': '168 22% 14%',
      '--accent-foreground': '150 20% 96%',
      '--destructive': '4 78% 52%',
      '--destructive-foreground': '0 0% 100%',
      '--border': '168 18% 16%',
      '--input': '168 22% 12%',
      '--ring': '152 78% 46%',
      '--card': '168 28% 8%',
      '--card-foreground': 'var(--foreground)',
      '--popover': '168 28% 8%',
      '--popover-foreground': 'var(--foreground)',
      '--sidebar-background': '170 40% 4%',
      '--sidebar-foreground': '150 18% 88%',
      '--sidebar-primary': '152 78% 48%',
      '--sidebar-primary-foreground': '170 40% 6%',
      '--sidebar-accent': '168 28% 11%',
      '--sidebar-accent-foreground': '150 25% 96%',
      '--sidebar-border': '168 20% 12%',
      '--sidebar-ring': '152 78% 48%',
      '--chart-1': '152 78% 48%',
      '--chart-2': '42 94% 55%',
      '--chart-3': '188 75% 52%',
      '--chart-4': '12 82% 58%',
      '--chart-5': '280 55% 62%',
    },
  },
  blue: {
    name: 'Blue',
    light: {
      '--background': '240 5% 96%',
      '--foreground': '240 5% 10%',
      '--primary': '221.2 83.2% 53.3%',
      '--primary-foreground': '210 40% 98%',
      '--secondary': '210 40% 96.1%',
      '--secondary-foreground': '222.2 47.4% 11.2%',
      '--muted': '240 5% 90%',
      '--muted-foreground': '240 5% 40%',
      '--accent': '240 5% 90%',
      '--accent-foreground': '222.2 47.4% 11.2%',
      '--destructive': '0 72% 51%',
      '--destructive-foreground': '0 0% 98%',
      '--border': '240 5% 80%',
      '--input': '240 6% 91%',
      '--ring': '221.2 83.2% 53.3%',
      '--card': '240 5% 98%',
      '--card-foreground': 'var(--foreground)',
      '--popover': 'var(--background)',
      '--popover-foreground': 'var(--foreground)',
      '--chart-1': '221.2 83.2% 53.3%',
      '--chart-2': '200 100% 50%',
      '--chart-3': '180 100% 50%',
      '--chart-4': '160 100% 50%',
      '--chart-5': '140 100% 50%',
    },
    dark: {
      '--background': '240 2% 11%',
      '--foreground': '0 0% 98%',
      '--primary': '217.2 91.2% 59.8%',
      '--primary-foreground': '222.2 47.4% 11.2%',
      '--secondary': '217.2 32.6% 17.5%',
      '--secondary-foreground': '210 40% 98%',
      '--muted': '217.2 32.6% 17.5%',
      '--muted-foreground': '0 0% 63.9%',
      '--accent': '217.2 32.6% 17.5%',
      '--accent-foreground': '210 40% 98%',
      '--destructive': '0 72% 51%',
      '--destructive-foreground': '210 40% 98%',
      '--border': '0 0% 18%',
      '--input': '240 2% 16.5%',
      '--ring': '215 16% 47%',
      '--card': '240 2% 11.5%',
      '--card-foreground': 'var(--foreground)',
      '--popover': 'var(--background)',
      '--popover-foreground': 'var(--foreground)',
      '--chart-1': '217.2 91.2% 59.8%',
      '--chart-2': '200 100% 60%',
      '--chart-3': '180 100% 60%',
      '--chart-4': '160 100% 60%',
      '--chart-5': '140 100% 60%',
    },
  },
  yellow: {
    name: 'Yellow',
    light: {
      '--background': '240 5% 96%',
      '--foreground': '240 5% 10%',
      '--primary': '47.9 95.8% 53.1%',
      '--primary-foreground': '26 83.3% 14.1%',
      '--secondary': '60 4.8% 95.9%',
      '--secondary-foreground': '24 9.8% 10%',
      '--muted': '240 5% 90%',
      '--muted-foreground': '240 5% 40%',
      '--accent': '240 5% 90%',
      '--accent-foreground': '24 9.8% 10%',
      '--destructive': '0 72% 51%',
      '--destructive-foreground': '0 0% 98%',
      '--border': '240 5% 80%',
      '--input': '240 6% 91%',
      '--ring': '20 14.3% 4.1%',
      '--card': '240 5% 98%',
      '--card-foreground': 'var(--foreground)',
      '--popover': 'var(--background)',
      '--popover-foreground': 'var(--foreground)',
      '--chart-1': '47.9 95.8% 53.1%',
      '--chart-2': '35 100% 50%',
      '--chart-3': '25 100% 50%',
      '--chart-4': '15 100% 50%',
      '--chart-5': '5 100% 50%',
    },
    dark: {
      '--background': '240 2% 11%',
      '--foreground': '0 0% 98%',
      '--primary': '47.9 95.8% 53.1%',
      '--primary-foreground': '26 83.3% 14.1%',
      '--secondary': '12 6.5% 15.1%',
      '--secondary-foreground': '60 9.1% 97.8%',
      '--muted': '12 6.5% 15.1%',
      '--muted-foreground': '0 0% 63.9%',
      '--accent': '12 6.5% 15.1%',
      '--accent-foreground': '60 9.1% 97.8%',
      '--destructive': '0 72% 51%',
      '--destructive-foreground': '210 40% 98%',
      '--border': '0 0% 18%',
      '--input': '240 2% 16.5%',
      '--ring': '215 16% 47%',
      '--card': '240 2% 11.5%',
      '--card-foreground': 'var(--foreground)',
      '--popover': 'var(--background)',
      '--popover-foreground': 'var(--foreground)',
      '--chart-1': '47.9 95.8% 53.1%',
      '--chart-2': '35 100% 60%',
      '--chart-3': '25 100% 60%',
      '--chart-4': '15 100% 60%',
      '--chart-5': '5 100% 60%',
    },
  },
  violet: {
    name: 'Violet',
    light: {
      '--background': '240 5% 96%',
      '--foreground': '240 5% 10%',
      '--primary': '262.1 83.3% 57.8%',
      '--primary-foreground': '210 20% 98%',
      '--secondary': '220 14.3% 95.9%',
      '--secondary-foreground': '220.9 39.3% 11%',
      '--muted': '240 5% 90%',
      '--muted-foreground': '240 5% 40%',
      '--accent': '240 5% 90%',
      '--accent-foreground': '220.9 39.3% 11%',
      '--destructive': '0 72% 51%',
      '--destructive-foreground': '0 0% 98%',
      '--border': '240 5% 80%',
      '--input': '240 6% 91%',
      '--ring': '262.1 83.3% 57.8%',
      '--card': '240 5% 98%',
      '--card-foreground': 'var(--foreground)',
      '--popover': 'var(--background)',
      '--popover-foreground': 'var(--foreground)',
      '--chart-1': '262.1 83.3% 57.8%',
      '--chart-2': '280 100% 50%',
      '--chart-3': '300 100% 50%',
      '--chart-4': '320 100% 50%',
      '--chart-5': '340 100% 50%',
    },
    dark: {
      '--background': '240 2% 11%',
      '--foreground': '0 0% 98%',
      '--primary': '263.4 70% 50.4%',
      '--primary-foreground': '210 20% 98%',
      '--secondary': '215 27.9% 16.9%',
      '--secondary-foreground': '210 20% 98%',
      '--muted': '215 27.9% 16.9%',
      '--muted-foreground': '0 0% 63.9%',
      '--accent': '215 27.9% 16.9%',
      '--accent-foreground': '210 20% 98%',
      '--destructive': '0 72% 51%',
      '--destructive-foreground': '210 40% 98%',
      '--border': '0 0% 18%',
      '--input': '240 2% 16.5%',
      '--ring': '215 16% 47%',
      '--card': '240 2% 11.5%',
      '--card-foreground': 'var(--foreground)',
      '--popover': 'var(--background)',
      '--popover-foreground': 'var(--foreground)',
      '--chart-1': '263.4 70% 50.4%',
      '--chart-2': '280 100% 60%',
      '--chart-3': '300 100% 60%',
      '--chart-4': '320 100% 60%',
      '--chart-5': '340 100% 60%',
    },
  },
}

const initialState: ThemeProviderState = {
  theme: 'system',
  colorTheme: 'default',
  radius: '0',
  resolvedTheme: 'light',
  setTheme: () => null,
  setColorTheme: () => null,
  setRadius: () => null,
  resetToDefaults: () => null,
  isSystemTheme: true,
}

const ThemeProviderContext = createContext<ThemeProviderState>(initialState)

// Helper function to safely access localStorage
const safeLocalStorage = {
  getItem: (key: string): string | null => {
    try {
      return localStorage.getItem(key)
    } catch (error) {
      console.warn(`Failed to get localStorage item ${key}:`, error)
      return null
    }
  },
  setItem: (key: string, value: string): boolean => {
    try {
      localStorage.setItem(key, value)
      return true
    } catch (error) {
      console.warn(`Failed to set localStorage item ${key}:`, error)
      return false
    }
  },
  removeItem: (key: string): boolean => {
    try {
      localStorage.removeItem(key)
      return true
    } catch (error) {
      console.warn(`Failed to remove localStorage item ${key}:`, error)
      return false
    }
  },
}

// Helper function to apply CSS variables
const applyThemeVars = (vars: Record<string, string>) => {
  const root = document.documentElement
  Object.entries(vars).forEach(([key, value]) => {
    root.style.setProperty(key, value)
  })
}

// Helper function to get system theme preference
const getSystemTheme = (): 'light' | 'dark' => {
  if (typeof window === 'undefined') return 'light'
  return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light'
}

export function ThemeProvider({
  children,
  defaultTheme = 'system',
  defaultColorTheme = 'default',
  defaultRadius = '0',
  storageKey = 'theme',
  colorStorageKey = 'color-theme',
  radiusStorageKey = 'radius',
  ...props
}: ThemeProviderProps) {
  // Load initial values from localStorage with fallbacks
  const [theme, setThemeState] = useState<Theme>(() => {
    const saved = safeLocalStorage.getItem(storageKey) as Theme
    return saved && ['light', 'dark', 'system'].includes(saved) ? saved : defaultTheme
  })

  const [colorTheme, setColorThemeState] = useState<ColorTheme>(() => {
    const saved = safeLocalStorage.getItem(colorStorageKey) as ColorTheme
    return saved && Object.keys(colorThemes).includes(saved) ? saved : defaultColorTheme
  })

  const [radius, setRadiusState] = useState<Radius>(() => {
    const saved = safeLocalStorage.getItem(radiusStorageKey) as Radius
    return saved && ['0', '0.3rem', '0.5rem', '0.75rem', '1rem'].includes(saved) ? saved : defaultRadius
  })

  const [resolvedTheme, setResolvedTheme] = useState<'light' | 'dark'>(() => {
    return theme === 'system' ? getSystemTheme() : theme === 'dark' ? 'dark' : 'light'
  })

  // Apply theme changes to DOM
  const applyTheme = useCallback((themeMode: 'light' | 'dark', colorThemeName: ColorTheme, radiusValue: Radius) => {
    const root = document.documentElement

    // Remove existing theme classes
    root.classList.remove('light', 'dark')
    root.classList.add(themeMode)

    // Apply color theme variables
    const colorThemeConfig = colorThemes[colorThemeName]
    if (colorThemeConfig) {
      const themeVars = colorThemeConfig[themeMode]
      applyThemeVars({
        ...themeVars,
        '--radius': radiusValue,
      })
    }
  }, [])

  // Handle system theme changes
  useEffect(() => {
    const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)')

    const handleChange = (e: MediaQueryListEvent) => {
      if (theme === 'system') {
        const systemTheme = e.matches ? 'dark' : 'light'
        setResolvedTheme(systemTheme)
        applyTheme(systemTheme, colorTheme, radius)
      }
    }

    mediaQuery.addEventListener('change', handleChange)
    return () => mediaQuery.removeEventListener('change', handleChange)
  }, [theme, colorTheme, radius, applyTheme])

  // Apply theme on mount and theme changes
  useEffect(() => {
    const newResolvedTheme = theme === 'system' ? getSystemTheme() : theme === 'dark' ? 'dark' : 'light'
    setResolvedTheme(newResolvedTheme)
    applyTheme(newResolvedTheme, colorTheme, radius)
  }, [theme, colorTheme, radius, applyTheme])

  // Enhanced setTheme function with error handling and toast
  const setTheme = useCallback(
    (newTheme: Theme) => {
      if (safeLocalStorage.setItem(storageKey, newTheme)) {
        setThemeState(newTheme)

        // Show success toast - this will be handled by the settings page
        // The provider itself shouldn't show toasts to avoid dependency issues
      } else {
        // Fallback: set theme without localStorage
        setThemeState(newTheme)
        console.warn('Failed to save theme to localStorage, changes may not persist')
      }
    },
    [storageKey],
  )

  // Enhanced setColorTheme function
  const setColorTheme = useCallback(
    (newColorTheme: ColorTheme) => {
      if (Object.keys(colorThemes).includes(newColorTheme)) {
        if (safeLocalStorage.setItem(colorStorageKey, newColorTheme)) {
          setColorThemeState(newColorTheme)
        } else {
          setColorThemeState(newColorTheme)
          console.warn('Failed to save color theme to localStorage, changes may not persist')
        }
      } else {
        console.warn(`Invalid color theme: ${newColorTheme}`)
      }
    },
    [colorStorageKey],
  )

  // Enhanced setRadius function
  const setRadius = useCallback(
    (newRadius: Radius) => {
      if (['0', '0.3rem', '0.5rem', '0.75rem'].includes(newRadius)) {
        if (safeLocalStorage.setItem(radiusStorageKey, newRadius)) {
          setRadiusState(newRadius)
        } else {
          setRadiusState(newRadius)
          console.warn('Failed to save radius to localStorage, changes may not persist')
        }
      } else {
        console.warn(`Invalid radius value: ${newRadius}`)
      }
    },
    [radiusStorageKey],
  )

  // Reset to defaults function
  const resetToDefaults = useCallback(() => {
    safeLocalStorage.removeItem(storageKey)
    safeLocalStorage.removeItem(colorStorageKey)
    safeLocalStorage.removeItem(radiusStorageKey)

    setThemeState(defaultTheme)
    setColorThemeState(defaultColorTheme)
    setRadiusState(defaultRadius)
  }, [storageKey, colorStorageKey, radiusStorageKey, defaultTheme, defaultColorTheme, defaultRadius])

  const value: ThemeProviderState = useMemo(
    () => ({
      theme,
      colorTheme,
      radius,
      resolvedTheme,
      setTheme,
      setColorTheme,
      setRadius,
      resetToDefaults,
      isSystemTheme: theme === 'system',
    }),
    [theme, colorTheme, radius, resolvedTheme, setTheme, setColorTheme, setRadius, resetToDefaults],
  )

  return (
    <ThemeProviderContext.Provider {...props} value={value}>
      {children}
    </ThemeProviderContext.Provider>
  )
}

export const useTheme = () => {
  const context = useContext(ThemeProviderContext)
  if (context === undefined) {
    throw new Error('useTheme must be used within a ThemeProvider')
  }
  return context
}

// Export color themes for use in components
export { colorThemes }
