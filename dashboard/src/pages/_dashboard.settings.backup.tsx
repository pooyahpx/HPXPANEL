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
  useBackups,
  useRestoreBackup,
  useRunBackup,
  useUpdateBackupConfig,
  type BackupConfig,
} from '@/service/api/backup'
import { formatBytes } from '@/utils/formatByte'
import { isOwner } from '@/utils/rbac'
import { AlertTriangle, CloudUpload, Database, Download, HardDriveDownload, Loader2, RefreshCcw, RotateCcw, Save } from 'lucide-react'
import { useEffect, useRef, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { toast } from 'sonner'

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
  const [config, setConfig] = useState<BackupConfig>(defaultConfig)
  const [restoreId, setRestoreId] = useState<string | null>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)

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
    try {
      const result = await restoreBackup.mutateAsync(restoreId)
      toast.success(result.message)
      setRestoreId(null)
    } catch (error: any) {
      toast.error(error?.data?.detail || t('settings.backup.restoreFailed'))
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
                <AlertDescription>{data.last_error}</AlertDescription>
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
                      <TableCell className="text-end">
                        <div className="flex justify-end gap-1">
                          <Button
                            size="icon"
                            variant="ghost"
                            onClick={() => downloadBackupFile(item.id, item.filename).catch(() => toast.error(t('downloadFailed')))}
                          >
                            <Download className="h-4 w-4" />
                          </Button>
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
                    <TableCell colSpan={6} className="text-muted-foreground py-8 text-center text-sm">
                      {t('settings.backup.empty')}
                    </TableCell>
                  </TableRow>
                )}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>

      <AlertDialog open={Boolean(restoreId)} onOpenChange={open => !open && setRestoreId(null)}>
        <AlertDialogContent dir={dir}>
          <AlertDialogHeader>
            <AlertDialogTitle>{t('settings.backup.restoreTitle')}</AlertDialogTitle>
            <AlertDialogDescription>{t('settings.backup.restorePrompt')}</AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>{t('cancel')}</AlertDialogCancel>
            <AlertDialogAction className={cn('bg-destructive text-destructive-foreground')} onClick={handleRestore} disabled={restoreBackup.isPending}>
              {t('settings.backup.restoreConfirm')}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  )
}
