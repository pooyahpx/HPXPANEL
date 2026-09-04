import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from '@/components/ui/card'
import useDirDetection from '@/hooks/use-dir-detection'
import { getAuthToken } from '@/utils/authStorage'
import { AlertTriangle, House, LogIn, RefreshCw } from 'lucide-react'
import { useTranslation } from 'react-i18next'
import { isRouteErrorResponse, useNavigate, useRouteError } from 'react-router'

export function DashboardRouteError() {
  const error = useRouteError()
  const navigate = useNavigate()
  const { t } = useTranslation()
  const dir = useDirDetection()
  const routeError = isRouteErrorResponse(error) ? error : null
  const shouldReturnToLogin = !getAuthToken() || routeError?.status === 401 || routeError?.status === 403
  const returnPath = shouldReturnToLogin ? '/login' : '/'
  const ReturnIcon = shouldReturnToLogin ? LogIn : House

  return (
    <main className="bg-background flex min-h-screen items-center justify-center px-4 py-10" dir={dir}>
      <Card className="w-full max-w-lg" role="alert" aria-live="assertive">
        <CardHeader className="items-center text-center">
          <div className="bg-destructive/10 text-destructive mb-2 flex h-14 w-14 items-center justify-center border-2 border-current">
            <AlertTriangle aria-hidden="true" className="h-7 w-7" />
          </div>
          <CardTitle className="text-2xl">{t('routeError.title')}</CardTitle>
          <CardDescription>{t('routeError.description')}</CardDescription>
        </CardHeader>
        <CardContent className="text-center">
          <p className="text-muted-foreground font-mono text-sm">
            {routeError ? t('routeError.status', { status: routeError.status }) : t('routeError.unknownStatus')}
          </p>
        </CardContent>
        <CardFooter className="flex flex-col-reverse gap-3 sm:flex-row sm:justify-center">
          <Button variant="outline" onClick={() => navigate(returnPath, { replace: true })}>
            <ReturnIcon aria-hidden="true" />
            {t(shouldReturnToLogin ? 'routeError.returnLogin' : 'routeError.returnDashboard')}
          </Button>
          <Button onClick={() => window.location.reload()}>
            <RefreshCw aria-hidden="true" />
            {t('routeError.reload')}
          </Button>
        </CardFooter>
      </Card>
    </main>
  )
}
