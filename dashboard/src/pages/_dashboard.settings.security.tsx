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
import { PasswordInput } from '@/components/ui/password-input'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import useDirDetection from '@/hooks/use-dir-detection'
import { useAdmin } from '@/hooks/use-admin'
import { cn } from '@/lib/utils'
import {
  useAdminSessions,
  useConfirmTotp,
  useDisableTotp,
  useRevokeAdminSession,
  useRevokeOtherAdminSessions,
  useSetupTotp,
} from '@/service/api/security'
import { KeyRound, Loader2, ShieldCheck, Trash2 } from 'lucide-react'
import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { toast } from 'sonner'

export default function SecuritySettings() {
  const { t } = useTranslation()
  const dir = useDirDetection()
  const { admin } = useAdmin()
  const totpEnabled = Boolean(admin?.totp_enabled)
  const { data: sessionsData, isLoading: sessionsLoading } = useAdminSessions()
  const setupTotp = useSetupTotp()
  const confirmTotp = useConfirmTotp()
  const disableTotp = useDisableTotp()
  const revokeSession = useRevokeAdminSession()
  const revokeOthers = useRevokeOtherAdminSessions()

  const [setupSecret, setSetupSecret] = useState<string | null>(null)
  const [otpauthUrl, setOtpauthUrl] = useState<string | null>(null)
  const [confirmCode, setConfirmCode] = useState('')
  const [disableCode, setDisableCode] = useState('')
  const [disablePassword, setDisablePassword] = useState('')
  const [revokeOthersOpen, setRevokeOthersOpen] = useState(false)

  const handleSetup = async () => {
    try {
      const result = await setupTotp.mutateAsync()
      setSetupSecret(result.secret)
      setOtpauthUrl(result.otpauth_url)
      toast.success(t('security.setupStarted'))
    } catch (error: any) {
      toast.error(error?.data?.detail || t('security.setupFailed'))
    }
  }

  const handleConfirm = async () => {
    try {
      await confirmTotp.mutateAsync(confirmCode)
      setSetupSecret(null)
      setOtpauthUrl(null)
      setConfirmCode('')
      toast.success(t('security.enabled'))
    } catch (error: any) {
      toast.error(error?.data?.detail || t('security.confirmFailed'))
    }
  }

  const handleDisable = async () => {
    try {
      await disableTotp.mutateAsync({ code: disableCode, password: disablePassword })
      setDisableCode('')
      setDisablePassword('')
      toast.success(t('security.disabled'))
    } catch (error: any) {
      toast.error(error?.data?.detail || t('security.disableFailed'))
    }
  }

  const handleRevoke = async (sessionId: number) => {
    try {
      await revokeSession.mutateAsync(sessionId)
      toast.success(t('security.sessionRevoked'))
    } catch (error: any) {
      toast.error(error?.data?.detail || t('security.sessionRevokeFailed'))
    }
  }

  const handleRevokeOthers = async () => {
    try {
      await revokeOthers.mutateAsync()
      setRevokeOthersOpen(false)
      toast.success(t('security.otherSessionsRevoked'))
    } catch (error: any) {
      toast.error(error?.data?.detail || t('security.sessionRevokeFailed'))
    }
  }

  return (
    <div className={cn('flex w-full flex-col gap-4', dir === 'rtl' && 'text-right')}>
      <Alert>
        <AlertDescription>{t('security.intro')}</AlertDescription>
      </Alert>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <ShieldCheck className="h-5 w-5" />
            {t('security.totpTitle')}
          </CardTitle>
          <CardDescription>{t('security.totpDescription')}</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <p className="text-sm">
            {t('security.status')}:{' '}
            <span className="font-medium">{totpEnabled ? t('security.enabledLabel') : t('security.disabledLabel')}</span>
          </p>

          {!totpEnabled && (
            <div className="space-y-3">
              <Button onClick={handleSetup} disabled={setupTotp.isPending}>
                {setupTotp.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : <KeyRound className="h-4 w-4" />}
                <span className="ms-2">{t('security.enableTotp')}</span>
              </Button>

              {setupSecret && (
                <div className="space-y-3 rounded-lg border p-4">
                  <div className="space-y-1">
                    <Label>{t('security.secret')}</Label>
                    <Input value={setupSecret} readOnly />
                  </div>
                  {otpauthUrl && (
                    <div className="space-y-1">
                      <Label>{t('security.otpauthUrl')}</Label>
                      <Input value={otpauthUrl} readOnly />
                    </div>
                  )}
                  <div className="space-y-1">
                    <Label htmlFor="confirm-code">{t('security.confirmCode')}</Label>
                    <Input
                      id="confirm-code"
                      inputMode="numeric"
                      autoComplete="one-time-code"
                      value={confirmCode}
                      onChange={e => setConfirmCode(e.target.value)}
                      placeholder="123456"
                    />
                  </div>
                  <Button onClick={handleConfirm} disabled={confirmTotp.isPending || confirmCode.length < 6}>
                    {confirmTotp.isPending && <Loader2 className="me-2 h-4 w-4 animate-spin" />}
                    {t('security.confirmEnable')}
                  </Button>
                </div>
              )}
            </div>
          )}

          {totpEnabled && (
            <div className="space-y-3 rounded-lg border p-4">
              <div className="space-y-1">
                <Label htmlFor="disable-code">{t('security.disableCode')}</Label>
                <Input
                  id="disable-code"
                  inputMode="numeric"
                  autoComplete="one-time-code"
                  value={disableCode}
                  onChange={e => setDisableCode(e.target.value)}
                />
              </div>
              <div className="space-y-1">
                <Label htmlFor="disable-password">{t('password')}</Label>
                <PasswordInput id="disable-password" value={disablePassword} onChange={e => setDisablePassword(e.target.value)} />
              </div>
              <Button variant="destructive" onClick={handleDisable} disabled={disableTotp.isPending}>
                {disableTotp.isPending && <Loader2 className="me-2 h-4 w-4 animate-spin" />}
                {t('security.disableTotp')}
              </Button>
            </div>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader className="flex flex-row items-start justify-between gap-4 space-y-0">
          <div>
            <CardTitle>{t('security.sessionsTitle')}</CardTitle>
            <CardDescription>{t('security.sessionsDescription')}</CardDescription>
          </div>
          <Button variant="outline" onClick={() => setRevokeOthersOpen(true)} disabled={revokeOthers.isPending}>
            {t('security.revokeOthers')}
          </Button>
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>{t('security.columns.ip')}</TableHead>
                <TableHead>{t('security.columns.userAgent')}</TableHead>
                <TableHead>{t('security.columns.created')}</TableHead>
                <TableHead>{t('security.columns.lastSeen')}</TableHead>
                <TableHead>{t('security.columns.actions')}</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {sessionsLoading ? (
                <TableRow>
                  <TableCell colSpan={5}>
                    <Loader2 className="h-4 w-4 animate-spin" />
                  </TableCell>
                </TableRow>
              ) : (sessionsData?.sessions?.length ?? 0) === 0 ? (
                <TableRow>
                  <TableCell colSpan={5} className="text-muted-foreground">
                    {t('security.noSessions')}
                  </TableCell>
                </TableRow>
              ) : (
                sessionsData?.sessions.map(session => (
                  <TableRow key={session.id}>
                    <TableCell>
                      {session.ip || '—'}
                      {session.current ? ` (${t('security.current')})` : ''}
                    </TableCell>
                    <TableCell className="max-w-[240px] truncate" title={session.user_agent || undefined}>
                      {session.user_agent || '—'}
                    </TableCell>
                    <TableCell>{new Date(session.created_at).toLocaleString()}</TableCell>
                    <TableCell>{session.last_seen_at ? new Date(session.last_seen_at).toLocaleString() : '—'}</TableCell>
                    <TableCell>
                      <Button
                        size="sm"
                        variant="ghost"
                        disabled={revokeSession.isPending}
                        onClick={() => handleRevoke(session.id)}
                      >
                        <Trash2 className="h-4 w-4" />
                      </Button>
                    </TableCell>
                  </TableRow>
                ))
              )}
            </TableBody>
          </Table>
        </CardContent>
      </Card>

      <AlertDialog open={revokeOthersOpen} onOpenChange={setRevokeOthersOpen}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>{t('security.revokeOthersTitle')}</AlertDialogTitle>
            <AlertDialogDescription>{t('security.revokeOthersPrompt')}</AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>{t('cancel')}</AlertDialogCancel>
            <AlertDialogAction onClick={handleRevokeOthers}>{t('security.revokeOthersConfirm')}</AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  )
}
