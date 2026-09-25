import { Alert, AlertDescription } from '@/components/ui/alert'
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from '@/components/ui/alert-dialog'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Switch } from '@/components/ui/switch'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import useDirDetection from '@/hooks/use-dir-detection'
import { useAdmin } from '@/hooks/use-admin'
import { cn } from '@/lib/utils'
import {
  downloadBackupFile,
  importBackupArchive,
  useBackupInstallTokens,
  useBackups,
  useCreateBackupInstallToken,
  useRestoreBackup,
  useRevokeBackupInstallToken,
  useRunBackup,
  useUpdateBackupConfig,
  useUpdateBackupInstallToken,
  useValidateBackup,
  type BackupConfig,
  type BackupInstallTokenResponse,
} from '@/service/api/backup'
import { formatBytes } from '@/utils/formatByte'
import { isOwner } from '@/utils/rbac'
import { AlertTriangle, CloudUpload, Database, Download, HardDriveDownload, KeyRound, Loader2, RefreshCcw, RotateCcw, Save, ShieldCheck, Trash2 } from 'lucide-react'
import { useEffect, useRef, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { toast } from 'sonner'

import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { Textarea } from '@/components/ui/textarea'
const defaultConfig: BackupConfig = {
  auto_enabled: false,
  schedule_hours: 24,
  local_retention: 14,
  upload_to_remote: true,
  remote: { enabled: false, host: '', port: 22, username: '', remote_path: '/var/backups/hpxpanel' },
}

export default function BackupSettings() {
  const { t } = useTranslation()
  const dir = useDirDetection()
  const { admin } = useAdmin()
  const owner = isOwner(admin)
  const { data, isLoading, refetch } = useBackups()
  const saveConfig = useUpdateBackupConfig()
  const runBackup = useRunBackup()
  const restoreBackup = useRestoreBackup()
  const validateBackup = useValidateBackup()
  const createInstallToken = useCreateBackupInstallToken()
  const { data: installTokensData, isLoading: installTokensLoading } = useBackupInstallTokens(owner)
  const updateInstallToken = useUpdateBackupInstallToken()
  const revokeInstallToken = useRevokeBackupInstallToken()
  const [config, setConfig] = useState<BackupConfig>(defaultConfig)
  const [restoreId, setRestoreId] = useState<string | null>(null)
  const [restoreError, setRestoreError] = useState<string | null>(null)
  const [revokeToken, setRevokeToken] = useState<string | null>(null)
  const [installLink, setInstallLink] = useState<BackupInstallTokenResponse | null>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)

  const apiErrorMessage = (error: unknown, fallback: string): string => {
    const e = error as {
      data?: { detail?: unknown }
      message?: string
      statusMessage?: string
      name?: string
    }
    if (e?.name === 'TimeoutError' || /timeout/i.test(String(e?.message || ''))) {
      return t('settings.backup.restoreTimeout', {
        defaultValue:
          'Restore timed out. Panel DB connections were blocking the drop. On the server run: hpxpanel restore',
      })
    }
    const detail = e?.data?.detail
    if (typeof detail === 'string' && detail.trim()) return detail.trim()
    if (Array.isArray(detail) && detail.length > 0) {
      const first = detail[0] as { msg?: string }
      if (typeof first?.msg === 'string' && first.msg.trim()) return first.msg.trim()
    }
    if (detail && typeof detail === 'object') {
      try {
        return JSON.stringify(detail)
      } catch {
        /* ignore */
      }
    }
    if (typeof e?.statusMessage === 'string' && e.statusMessage.trim()) return e.statusMessage.trim()
    if (typeof e?.message === 'string' && e.message.trim() && e.message !== '[GET] ""') return e.message.trim()
    return fallback
  }

  useEffect(() => {
    if (data?.config) setConfig(data.config)
  }, [data?.config])

  const handleSave = async () => {
    try {
      await saveConfig.mutateAsync(config)
      toast.success(t('settings.backup.saveSuccess'))
    } catch (error: any) {
      toast.error(error?.data?.detail || t('settings.backup.saveFailed'))
    }
  }

  const handleRun = async () => {
    try {
      const result = await runBackup.mutateAsync()
      toast.success(result.message || t('settings.backup.runSuccess'))
    } catch (error: any) {
      toast.error(error?.data?.detail || t('settings.backup.runFailed'))
    }
  }

  const handleRestore = async () => {
    if (!restoreId) return
    const id = restoreId
    setRestoreError(null)
    try {
      const result = await restoreBackup.mutateAsync(id)
      toast.success(result.message || t('settings.backup.restoreSuccess', { defaultValue: 'Database restored' }))
      setRestoreId(null)
      await refetch()
    } catch (error: unknown) {
      const msg = apiErrorMessage(error, t('settings.backup.restoreFailed'))
      setRestoreError(msg)
      toast.error(msg, { duration: 15000 })
      await refetch()
    }
  }

  const handleValidate = async (backupId: string) => {
    try {
      const result = await validateBackup.mutateAsync(backupId)
      toast.success(result.message || t('settings.backup.dryRunSuccess'))
    } catch (error: any) {
      toast.error(error?.data?.detail || t('settings.backup.dryRunFailed'))
    }
  }

  const handleImport = async (file: File) => {
    try {
      const result = await importBackupArchive(file)
      toast.success(result.message)
      await refetch()
    } catch (error: any) {
      toast.error(error?.data?.detail || t('settings.backup.importFailed'))
    }
  }

  const handleInstallToken = async (backupId: string) => {
    try {
      const result = await createInstallToken.mutateAsync(backupId)
      setInstallLink(result)
      await navigator.clipboard.writeText(result.install_command)
      toast.success(t('settings.backup.installTokenCopied', { defaultValue: 'Install command copied' }))
    } catch (error: any) {
      toast.error(error?.data?.detail || t('settings.backup.installTokenFailed', { defaultValue: 'Could not create install token' }))
    }
  }

  const handleToggleToken = async (token: string, enabled: boolean) => {
    try {
      await updateInstallToken.mutateAsync({ token, enabled })
      toast.success(
        enabled
          ? t('settings.backup.installTokenEnabled', { defaultValue: 'Install token enabled' })
          : t('settings.backup.installTokenDisabled', { defaultValue: 'Install token disabled' }),
      )
    } catch (error: any) {
      toast.error(error?.data?.detail || t('settings.backup.installTokenFailed', { defaultValue: 'Could not update install token' }))
    }
  }

  const handleRevokeToken = async () => {
    if (!revokeToken) return
    try {
      await revokeInstallToken.mutateAsync(revokeToken)
      toast.success(t('settings.backup.installTokenRevoked', { defaultValue: 'Install token revoked' }))
      setRevokeToken(null)
    } catch (error: any) {
      toast.error(error?.data?.detail || t('settings.backup.installTokenFailed', { defaultValue: 'Could not revoke install token' }))
    }
  }

  return (
    <div dir={dir} className="space-y-6">
      <Alert>
        <Database className="h-4 w-4" />
        <AlertDescription>{t('settings.backup.intro')}</AlertDescription>
      </Alert>

      {!owner && (
        <Alert variant="destructive">
          <AlertTriangle className="h-4 w-4" />
          <AlertDescription>{t('settings.backup.ownerOnly')}</AlertDescription>
        </Alert>
      )}

      <div className="grid gap-6 xl:grid-cols-2">
        <Card className="rounded-none">
          <CardHeader>
            <CardTitle>{t('settings.backup.configTitle')}</CardTitle>
            <CardDescription>{t('settings.backup.configDescription')}</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex items-center justify-between gap-3">
              <Label htmlFor="auto_enabled">{t('settings.backup.autoEnabled')}</Label>
              <Switch id="auto_enabled" checked={config.auto_enabled} disabled={!owner} onCheckedChange={v => setConfig(c => ({ ...c, auto_enabled: v }))} />
            </div>
            <div className="space-y-2">
              <Label htmlFor="schedule_hours">{t('settings.backup.scheduleHours')}</Label>
              <Input id="schedule_hours" type="number" min={1} max={168} disabled={!owner} value={config.schedule_hours} onChange={e => setConfig(c => ({ ...c, schedule_hours: Number(e.target.value) }))} />
            </div>
            <div className="space-y-2">
              <Label htmlFor="local_retention">{t('settings.backup.localRetention')}</Label>
              <Input id="local_retention" type="number" min={1} max={365} disabled={!owner} value={config.local_retention} onChange={e => setConfig(c => ({ ...c, local_retention: Number(e.target.value) }))} />
            </div>
            <div className="flex items-center justify-between gap-3">
              <Label htmlFor="upload_to_remote">{t('settings.backup.uploadToRemote')}</Label>
              <Switch id="upload_to_remote" checked={config.upload_to_remote} disabled={!owner} onCheckedChange={v => setConfig(c => ({ ...c, upload_to_remote: v }))} />
            </div>
            <div className="border-t pt-4">
              <div className="mb-3 flex items-center gap-2 font-medium">
                <CloudUpload className="h-4 w-4" />
                {t('settings.backup.sftpTitle')}
              </div>
              <div className="space-y-3">
                <div className="flex items-center justify-between gap-3">
                  <Label>{t('settings.backup.sftpEnabled')}</Label>
                  <Switch checked={config.remote.enabled} disabled={!owner} onCheckedChange={v => setConfig(c => ({ ...c, remote: { ...c.remote, enabled: v } }))} />
                </div>
                <Input placeholder="backup.example.com" disabled={!owner} value={config.remote.host} onChange={e => setConfig(c => ({ ...c, remote: { ...c.remote, host: e.target.value } }))} />
                <div className="grid grid-cols-2 gap-3">
                  <Input type="number" placeholder="22" disabled={!owner} value={config.remote.port} onChange={e => setConfig(c => ({ ...c, remote: { ...c.remote, port: Number(e.target.value) } }))} />
                  <Input placeholder="backup-user" disabled={!owner} value={config.remote.username} onChange={e => setConfig(c => ({ ...c, remote: { ...c.remote, username: e.target.value } }))} />
                </div>
                <Input placeholder="/var/backups/hpxpanel" disabled={!owner} value={config.remote.remote_path} onChange={e => setConfig(c => ({ ...c, remote: { ...c.remote, remote_path: e.target.value } }))} />
                <p className="text-muted-foreground text-xs">{t('settings.backup.sftpSecretHint')}</p>
                <p className="text-muted-foreground text-xs">{t('settings.backup.encryptionHint')}</p>
              </div>
            </div>
            {owner && (
              <Button onClick={handleSave} disabled={saveConfig.isPending} className="w-full">
                {saveConfig.isPending ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <Save className="mr-2 h-4 w-4" />}
                {t('save')}
              </Button>
            )}
          </CardContent>
        </Card>

        <Card className="rounded-none">
          <CardHeader>
            <CardTitle>{t('settings.backup.actionsTitle')}</CardTitle>
            <CardDescription>{t('settings.backup.actionsDescription')}</CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
              <Button onClick={handleRun} disabled={!owner || runBackup.isPending || data?.status === 'running'}>
                {runBackup.isPending || data?.status === 'running' ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <HardDriveDownload className="mr-2 h-4 w-4" />}
                {t('settings.backup.runNow')}
              </Button>
              <Button variant="outline" onClick={() => refetch()}>
                <RefreshCcw className="mr-2 h-4 w-4" />
                {t('refresh')}
              </Button>
              <Button variant="outline" disabled={!owner} onClick={() => fileInputRef.current?.click()}>
                <CloudUpload className="mr-2 h-4 w-4" />
                {t('settings.backup.importArchive')}
              </Button>
              <input ref={fileInputRef} type="file" accept=".zip" className="hidden" onChange={e => e.target.files?.[0] && handleImport(e.target.files[0])} />
            </div>
            {data?.last_error && (
              <Alert variant="destructive">
                <AlertTriangle className="h-4 w-4" />
                <AlertDescription className="break-words whitespace-pre-wrap">{data.last_error}</AlertDescription>
              </Alert>
            )}
            <Alert>
              <RotateCcw className="h-4 w-4" />
              <AlertDescription>{t('settings.backup.restoreHint')}</AlertDescription>
            </Alert>
          </CardContent>
        </Card>
      </div>

      <Card className="rounded-none">
        <CardHeader>
          <CardTitle>{t('settings.backup.historyTitle')}</CardTitle>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <div className="flex justify-center py-8">
              <Loader2 className="h-6 w-6 animate-spin" />
            </div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>{t('settings.backup.columns.date')}</TableHead>
                  <TableHead>{t('settings.backup.columns.engine')}</TableHead>
                  <TableHead>{t('settings.backup.columns.version')}</TableHead>
                  <TableHead>{t('settings.backup.columns.size')}</TableHead>
                  <TableHead>{t('settings.backup.columns.remote')}</TableHead>
                  <TableHead>{t('settings.backup.columns.encrypted')}</TableHead>
                  <TableHead className="text-end">{t('actions')}</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {data?.items?.length ? (
                  data.items.map(item => (
                    <TableRow key={item.id}>
                      <TableCell className="font-mono text-xs">{new Date(item.created_at).toLocaleString()}</TableCell>
                      <TableCell>{item.database_engine}</TableCell>
                      <TableCell>{item.panel_version}</TableCell>
                      <TableCell>{formatBytes(item.size_bytes, 1, true, false)}</TableCell>
                      <TableCell>{item.remote_uploaded ? '✓' : '—'}</TableCell>
                      <TableCell>{item.encrypted ? '✓' : '—'}</TableCell>
                      <TableCell className="text-end">
                        <div className="flex justify-end gap-1">
                          <Button
                            size="icon"
                            variant="ghost"
                            title={t('settings.backup.dryRun')}
                            disabled={!owner || validateBackup.isPending}
                            onClick={() => handleValidate(item.id)}
                          >
                            <ShieldCheck className="h-4 w-4" />
                          </Button>
                          <Button
                            size="icon"
                            variant="ghost"
                            onClick={() => downloadBackupFile(item.id, item.filename).catch(() => toast.error(t('downloadFailed')))}
                          >
                            <Download className="h-4 w-4" />
                          </Button>
                          {owner && (
                            <Button
                              size="icon"
                              variant="ghost"
                              title={t('settings.backup.installToken', { defaultValue: 'Install with this backup' })}
                              disabled={createInstallToken.isPending}
                              onClick={() => handleInstallToken(item.id)}
                            >
                              <KeyRound className="h-4 w-4" />
                            </Button>
                          )}
                          {owner && (
                            <Button size="icon" variant="ghost" onClick={() => setRestoreId(item.id)}>
                              <RotateCcw className="h-4 w-4" />
                            </Button>
                          )}
                        </div>
                      </TableCell>
                    </TableRow>
                  ))
                ) : (
                  <TableRow>
                    <TableCell colSpan={7} className="text-muted-foreground py-8 text-center text-sm">
                      {t('settings.backup.empty')}
                    </TableCell>
                  </TableRow>
                )}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>

      {owner && (
        <Card className="rounded-none">
          <CardHeader>
            <CardTitle>{t('settings.backup.installTokensTitle', { defaultValue: 'Install tokens' })}</CardTitle>
            <CardDescription>
              {t('settings.backup.installTokensDescription', {
                defaultValue: 'See which IP / datacenter used a restore link, and disable or revoke access.',
              })}
            </CardDescription>
          </CardHeader>
          <CardContent>
            {installTokensLoading ? (
              <div className="text-muted-foreground flex items-center gap-2 text-sm">
                <Loader2 className="h-4 w-4 animate-spin" />
                {t('loading')}
              </div>
            ) : (
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>{t('settings.backup.created', { defaultValue: 'Created' })}</TableHead>
                    <TableHead>{t('settings.backup.backupId', { defaultValue: 'Backup' })}</TableHead>
                    <TableHead>{t('settings.backup.lastIp', { defaultValue: 'Last IP' })}</TableHead>
                    <TableHead>{t('settings.backup.datacenter', { defaultValue: 'Datacenter' })}</TableHead>
                    <TableHead>{t('settings.backup.uses', { defaultValue: 'Uses' })}</TableHead>
                    <TableHead>{t('settings.backup.enabled', { defaultValue: 'Enabled' })}</TableHead>
                    <TableHead className="text-end">{t('actions')}</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {installTokensData?.items?.length ? (
                    installTokensData.items.map(item => (
                      <TableRow key={item.token} className={item.revoked ? 'opacity-60' : undefined}>
                        <TableCell className="font-mono text-xs">
                          {item.created_at ? new Date(item.created_at).toLocaleString() : '—'}
                        </TableCell>
                        <TableCell className="max-w-[140px] truncate font-mono text-xs" title={item.backup_id}>
                          {item.backup_id}
                        </TableCell>
                        <TableCell className="font-mono text-xs" dir="ltr">
                          {item.last_used_ip || '—'}
                          {item.last_used_country_code ? (
                            <span className="text-muted-foreground ml-1">({item.last_used_country_code})</span>
                          ) : null}
                        </TableCell>
                        <TableCell className="max-w-[180px] truncate text-xs" title={item.last_used_isp || ''}>
                          {item.last_used_isp || '—'}
                          {item.last_used_city ? (
                            <span className="text-muted-foreground block truncate">{item.last_used_city}</span>
                          ) : null}
                        </TableCell>
                        <TableCell>{item.use_count}</TableCell>
                        <TableCell>
                          <Switch
                            checked={item.enabled && !item.revoked}
                            disabled={item.revoked || updateInstallToken.isPending}
                            onCheckedChange={v => handleToggleToken(item.token, v)}
                          />
                        </TableCell>
                        <TableCell className="text-end">
                          <Button
                            size="icon"
                            variant="ghost"
                            title={t('settings.backup.revokeToken', { defaultValue: 'Revoke' })}
                            disabled={item.revoked || revokeInstallToken.isPending}
                            onClick={() => setRevokeToken(item.token)}
                          >
                            <Trash2 className="h-4 w-4" />
                          </Button>
                        </TableCell>
                      </TableRow>
                    ))
                  ) : (
                    <TableRow>
                      <TableCell colSpan={7} className="text-muted-foreground py-8 text-center text-sm">
                        {t('settings.backup.installTokensEmpty', {
                          defaultValue: 'No install tokens yet. Create one from a backup row.',
                        })}
                      </TableCell>
                    </TableRow>
                  )}
                </TableBody>
              </Table>
            )}
          </CardContent>
        </Card>
      )}

      <AlertDialog
        open={Boolean(restoreId)}
        onOpenChange={open => {
          // Keep dialog open while restore runs — AlertDialogAction used to close
          // immediately, so failures looked like "nothing happened".
          if (!open && restoreBackup.isPending) return
          if (!open) {
            setRestoreId(null)
            setRestoreError(null)
          }
        }}
      >
        <AlertDialogContent dir={dir}>
          <AlertDialogHeader>
            <AlertDialogTitle>{t('settings.backup.restoreTitle')}</AlertDialogTitle>
            <AlertDialogDescription>{t('settings.backup.restorePrompt')}</AlertDialogDescription>
          </AlertDialogHeader>
          {restoreBackup.isPending && (
            <Alert>
              <Loader2 className="h-4 w-4 animate-spin" />
              <AlertDescription>
                {t('settings.backup.restoreInProgress', {
                  defaultValue: 'Restoring database… this can take a minute. Keep this window open.',
                })}
              </AlertDescription>
            </Alert>
          )}
          {restoreError && (
            <Alert variant="destructive">
              <AlertTriangle className="h-4 w-4" />
              <AlertDescription className="break-words whitespace-pre-wrap">{restoreError}</AlertDescription>
            </Alert>
          )}
          <AlertDialogFooter>
            <AlertDialogCancel disabled={restoreBackup.isPending}>{t('cancel')}</AlertDialogCancel>
            <Button
              type="button"
              variant="destructive"
              disabled={restoreBackup.isPending}
              onClick={() => void handleRestore()}
            >
              {restoreBackup.isPending ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : null}
              {t('settings.backup.restoreConfirm')}
            </Button>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>

      <AlertDialog open={Boolean(revokeToken)} onOpenChange={open => !open && setRevokeToken(null)}>
        <AlertDialogContent dir={dir}>
          <AlertDialogHeader>
            <AlertDialogTitle>{t('settings.backup.revokeTokenTitle', { defaultValue: 'Revoke install token?' })}</AlertDialogTitle>
            <AlertDialogDescription>
              {t('settings.backup.revokeTokenPrompt', {
                defaultValue: 'The restore URL will stop working immediately. This cannot be undone.',
              })}
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>{t('cancel')}</AlertDialogCancel>
            <AlertDialogAction className={cn('bg-destructive text-destructive-foreground')} onClick={handleRevokeToken} disabled={revokeInstallToken.isPending}>
              {t('settings.backup.revokeTokenConfirm', { defaultValue: 'Revoke' })}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>

      <Dialog open={Boolean(installLink)} onOpenChange={open => !open && setInstallLink(null)}>
        <DialogContent dir={dir} className="sm:max-w-xl">
          <DialogHeader>
            <DialogTitle>{t('settings.backup.installTokenTitle', { defaultValue: 'Install with backup' })}</DialogTitle>
            <DialogDescription>
              {t('settings.backup.installTokenHint', {
                defaultValue:
                  'Keep this panel online until the new server finishes downloading. Token expires automatically.',
              })}
            </DialogDescription>
          </DialogHeader>
          {installLink ? (
            <div className="space-y-3">
              <p className="text-muted-foreground text-xs">
                {t('settings.backup.installTokenExpires', {
                  defaultValue: 'Expires',
                })}
                : {new Date(installLink.expires_at).toLocaleString()}
              </p>
              <Textarea className="font-mono text-xs" readOnly rows={5} value={installLink.install_command} dir="ltr" />
              <p className="text-muted-foreground text-xs break-all" dir="ltr">
                {installLink.restore_url}
              </p>
            </div>
          ) : null}
          <DialogFooter>
            <Button
              type="button"
              onClick={async () => {
                if (!installLink) return
                await navigator.clipboard.writeText(installLink.install_command)
                toast.success(t('settings.backup.installTokenCopied', { defaultValue: 'Install command copied' }))
              }}
            >
              {t('copy', { defaultValue: 'Copy' })}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}
