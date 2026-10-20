'use client'

import { Language } from '@/components/common/language'
import { ThemeToggle } from '@/components/common/theme-toggle'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import { Progress } from '@/components/ui/progress'
import { statusColors } from '@/constants/UserSettings'
import { useAdmin } from '@/hooks/use-admin'
import { cn } from '@/lib/utils'
import { removeAuthToken } from '@/utils/authStorage'
import { formatBytes } from '@/utils/formatByte'
import { queryClient } from '@/utils/query-client'
import { isOwner, roleLabel } from '@/utils/rbac'
import { ChartNoAxesColumn, ChartPie, ChevronsUpDown, LogOut, UserRound, UserRoundKey, UsersIcon } from 'lucide-react'
import { useTranslation } from 'react-i18next'
import { useNavigate } from 'react-router'

const isLimitActive = (limit: number | null | undefined): limit is number => typeof limit === 'number' && limit > 0

const getProgressPct = (used: number, total: number) => {
  if (total <= 0) return 0
  return Math.min(100, Math.max(0, (used / total) * 100))
}

/** Glass header account chip — stable outside the hover rail so logout stays clickable. */
export function HeaderUserMenu({ className }: { className?: string }) {
  const { t } = useTranslation()
  const { admin } = useAdmin()
  const navigate = useNavigate()

  if (!admin) return null

  const username = admin.username || 'admin'
  const initial = username.slice(0, 1).toUpperCase()
  const RoleIcon = isOwner(admin) ? UserRoundKey : UserRound
  const dataLimit = admin.data_limit ?? null
  const overrides = admin.permission_overrides ?? null
  const roleLimits = admin.role?.limits ?? null
  const maxUsers =
    overrides?.max_users != null ? overrides.max_users : roleLimits?.max_users != null ? roleLimits.max_users : null
  const hasDataLimit = isLimitActive(dataLimit)
  const hasUserLimit = isLimitActive(maxUsers)
  const usedTraffic = admin.used_traffic ?? 0
  const totalUsers = admin.total_users ?? 0
  const sliderColor = statusColors[admin.status ?? 'active']?.sliderColor

  const handleLogout = (e: React.MouseEvent) => {
    e.preventDefault()
    queryClient.cancelQueries()
    removeAuthToken()
    queryClient.clear()
    navigate('/login', { replace: true })
  }

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button
          type="button"
          variant="outline"
          aria-label={t('header.accountMenu', { defaultValue: 'Account menu' })}
          className={cn(
            'border-border/60 bg-card/45 hover:bg-card/70 h-9 cursor-pointer gap-2 rounded-xl px-2.5 shadow-[0_8px_24px_-18px_hsl(0_0%_0%/0.55)] backdrop-blur-md transition-[background-color,border-color,box-shadow] duration-200',
            'focus-visible:ring-ring focus-visible:ring-2',
            className,
          )}
        >
          <span className="bg-primary/20 text-primary inline-flex h-6 w-6 shrink-0 items-center justify-center rounded-lg text-[11px] font-bold">
            {initial}
          </span>
          <span className="hidden min-w-0 text-start sm:block">
            <span className="block max-w-[7.5rem] truncate text-xs font-semibold leading-tight">{username}</span>
            <span className="text-muted-foreground block font-mono text-[10px] leading-tight tabular-nums" dir="ltr">
              {formatBytes(usedTraffic)}
            </span>
          </span>
          <ChevronsUpDown className="text-muted-foreground hidden h-3.5 w-3.5 shrink-0 sm:block" />
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" sideOffset={8} className="border-border/70 bg-popover/95 w-72 rounded-2xl p-2 shadow-xl backdrop-blur-xl">
        <DropdownMenuLabel className="p-0 font-normal">
          <div className="flex items-start gap-3 rounded-xl px-2 py-2.5">
            <span className="bg-primary/20 text-primary mt-0.5 inline-flex h-9 w-9 shrink-0 items-center justify-center rounded-xl text-sm font-bold">
              {initial}
            </span>
            <div className="min-w-0 flex-1">
              <div className="flex flex-wrap items-center gap-1.5">
                <span className="truncate text-sm font-semibold">{username}</span>
                <Badge variant={isOwner(admin) ? 'secondary' : 'outline'} className="h-4 gap-1 px-1.5 py-0 text-[10px]">
                  <RoleIcon className="size-3" />
                  {roleLabel(admin)}
                </Badge>
              </div>
              <p className="text-muted-foreground mt-1 text-[11px]">{t('header.signedIn', { defaultValue: 'Signed in' })}</p>
            </div>
          </div>
        </DropdownMenuLabel>

        <div className="text-muted-foreground space-y-2.5 px-2 py-2 text-xs">
          <div className="space-y-1">
            <div className="flex items-center justify-between gap-2">
              <span className="inline-flex items-center gap-1.5">
                <ChartPie className="size-3.5" />
                {t('admins.used.traffic')}
              </span>
              <span className="font-medium tabular-nums" dir="ltr">
                {formatBytes(usedTraffic)}
                {hasDataLimit ? ` / ${formatBytes(dataLimit)}` : ''}
              </span>
            </div>
            {hasDataLimit && <Progress indicatorClassName={sliderColor} value={getProgressPct(usedTraffic, dataLimit)} className="h-1" />}
          </div>
          <div className="flex items-center justify-between gap-2">
            <span className="inline-flex items-center gap-1.5">
              <ChartNoAxesColumn className="size-3.5" />
              {t('statistics.totalUsage')}
            </span>
            <span className="font-medium tabular-nums" dir="ltr">
              {formatBytes(admin.lifetime_used_traffic || 0)}
            </span>
          </div>
          <div className="space-y-1">
            <div className="flex items-center justify-between gap-2">
              <span className="inline-flex items-center gap-1.5">
                <UsersIcon className="size-3.5" />
                {t('admins.total.users')}
              </span>
              <span className="font-medium tabular-nums" dir="ltr">
                {totalUsers}
                {hasUserLimit ? ` / ${maxUsers}` : ''}
              </span>
            </div>
            {hasUserLimit && <Progress indicatorClassName={sliderColor} value={getProgressPct(totalUsers, maxUsers)} className="h-1" />}
          </div>
        </div>

        <DropdownMenuSeparator />

        <div className="flex items-center gap-1.5 px-1 py-1 sm:hidden">
          <ThemeToggle />
          <Language />
        </div>
        <div className="sm:hidden">
          <DropdownMenuSeparator />
        </div>

        <DropdownMenuItem
          onClick={handleLogout}
          className="text-destructive focus:text-destructive focus:bg-destructive/10 cursor-pointer rounded-xl"
        >
          <LogOut className="mr-2 size-4" />
          {t('header.logout')}
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  )
}
