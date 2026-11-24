import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { LoaderButton } from '@/components/ui/loader-button'
import {
  applyHostCoefficientToAll,
  deleteHostUserCoefficient,
  getHostUserCoefficients,
  upsertHostUserCoefficient,
  type UserHostCoefficientItem,
} from '@/service/api'
import { Loader2, Trash2, Users } from 'lucide-react'
import { useCallback, useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { toast } from 'sonner'

type Props = {
  hostId: number
  hostCoefficient: number
}

export function HostCoefficientOverrides({ hostId, hostCoefficient }: Props) {
  const { t } = useTranslation()
  const [items, setItems] = useState<UserHostCoefficientItem[]>([])
  const [loading, setLoading] = useState(true)
  const [username, setUsername] = useState('')
  const [coeff, setCoeff] = useState('1')
  const [saving, setSaving] = useState(false)
  const [applying, setApplying] = useState(false)

  const reload = useCallback(async () => {
    setLoading(true)
    try {
      const rows = await getHostUserCoefficients(hostId)
      setItems(rows)
    } catch {
      toast.error(t('hostsDialog.coefficient.loadFailed', { defaultValue: 'Failed to load per-user coefficients' }))
    } finally {
      setLoading(false)
    }
  }, [hostId, t])

  useEffect(() => {
    void reload()
  }, [reload])

  const handleUpsert = async () => {
    const name = username.trim()
    const value = Number.parseFloat(coeff)
    if (!name) {
      toast.error(t('hostsDialog.coefficient.usernameRequired', { defaultValue: 'Enter a username' }))
      return
    }
    if (!Number.isFinite(value) || value <= 0) {
      toast.error(t('hostsDialog.coefficient.invalid', { defaultValue: 'Coefficient must be greater than 0' }))
      return
    }
    setSaving(true)
    try {
      await upsertHostUserCoefficient(hostId, { username: name, usage_coefficient: value })
      toast.success(t('hostsDialog.coefficient.saved', { defaultValue: 'Per-user coefficient saved' }))
      setUsername('')
      setCoeff(String(hostCoefficient || 1))
      await reload()
    } catch (error: any) {
      toast.error(
        error?.data?.detail ||
          error?.message ||
          t('hostsDialog.coefficient.saveFailed', { defaultValue: 'Failed to save per-user coefficient' }),
      )
    } finally {
      setSaving(false)
    }
  }

  const handleDelete = async (name: string) => {
    try {
      await deleteHostUserCoefficient(hostId, name)
      toast.success(t('hostsDialog.coefficient.removed', { defaultValue: 'Override removed' }))
      await reload()
    } catch (error: any) {
      toast.error(
        error?.data?.detail ||
          error?.message ||
          t('hostsDialog.coefficient.removeFailed', { defaultValue: 'Failed to remove override' }),
      )
    }
  }

  const handleApplyAll = async () => {
    const value = Number(hostCoefficient)
    const payload = Number.isFinite(value) && value > 0 ? { usage_coefficient: value } : {}
    setApplying(true)
    try {
      const result = await applyHostCoefficientToAll(hostId, payload)
      toast.success(
        t('hostsDialog.coefficient.applyAllSuccess', {
          count: result.users_updated,
          coeff: result.usage_coefficient,
          defaultValue: 'Applied ×{{coeff}} to {{count}} users',
        }),
      )
      await reload()
    } catch (error: any) {
      toast.error(
        error?.data?.detail ||
          error?.message ||
          t('hostsDialog.coefficient.applyAllFailed', { defaultValue: 'Failed to apply coefficient to all users' }),
      )
    } finally {
      setApplying(false)
    }
  }

  return (
    <div className="bg-muted/15 space-y-3 rounded-sm border p-3">
      <div className="flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
        <div className="space-y-1">
          <p className="text-sm font-medium">
            {t('hostsDialog.coefficient.overridesTitle', { defaultValue: 'Per-user overrides' })}
          </p>
          <p className="text-muted-foreground text-xs leading-relaxed">
            {t('hostsDialog.coefficient.overridesHint', {
              defaultValue: 'Override this config’s coefficient for one user, or push the host coefficient to everyone who can use it.',
            })}
          </p>
        </div>
        <LoaderButton
          type="button"
          variant="outline"
          size="sm"
          className="cursor-pointer shrink-0"
          isLoading={applying}
          onClick={() => void handleApplyAll()}
        >
          <Users className="mr-1.5 h-3.5 w-3.5" />
          {t('hostsDialog.coefficient.applyAll', { defaultValue: 'Apply to all users' })}
        </LoaderButton>
      </div>

      <div className="grid gap-2 sm:grid-cols-[minmax(0,1.4fr)_minmax(0,0.8fr)_auto]">
        <Input
          placeholder={t('username', { defaultValue: 'Username' })}
          value={username}
          onChange={e => setUsername(e.target.value)}
          autoComplete="off"
        />
        <Input
          type="number"
          min={0.01}
          step="any"
          placeholder="1"
          value={coeff}
          onChange={e => setCoeff(e.target.value)}
        />
        <LoaderButton type="button" size="sm" className="cursor-pointer" isLoading={saving} onClick={() => void handleUpsert()}>
          {t('hostsDialog.coefficient.set', { defaultValue: 'Set' })}
        </LoaderButton>
      </div>

      {loading ? (
        <div className="text-muted-foreground flex items-center gap-2 py-2 text-xs">
          <Loader2 className="h-3.5 w-3.5 animate-spin" />
          {t('loading', { defaultValue: 'Loading...' })}
        </div>
      ) : items.length === 0 ? (
        <p className="text-muted-foreground text-xs">
          {t('hostsDialog.coefficient.emptyOverrides', { defaultValue: 'No per-user overrides yet.' })}
        </p>
      ) : (
        <ul className="divide-border max-h-40 space-y-0 overflow-y-auto rounded-sm border">
          {items.map(item => (
            <li key={item.user_id} className="flex items-center justify-between gap-2 border-b px-2.5 py-1.5 last:border-b-0">
              <div className="min-w-0">
                <p className="truncate text-sm font-medium">{item.username}</p>
                <p className="text-muted-foreground font-mono text-[11px]">×{item.usage_coefficient}</p>
              </div>
              <Button
                type="button"
                variant="ghost"
                size="icon"
                className="text-destructive hover:text-destructive h-8 w-8 cursor-pointer"
                onClick={() => void handleDelete(item.username)}
              >
                <Trash2 className="h-3.5 w-3.5" />
              </Button>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}
