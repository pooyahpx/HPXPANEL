import { Button } from '@/components/ui/button'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Sheet, SheetContent, SheetDescription, SheetHeader, SheetTitle } from '@/components/ui/sheet'
import { Textarea } from '@/components/ui/textarea'
import { sendCopilotChat, type CopilotMessage } from '@/service/api/copilot'
import { cn } from '@/lib/utils'
import { Bot, ExternalLink, Loader2, Send, Sparkles, User } from 'lucide-react'
import { useCallback, useEffect, useRef, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { useLocation } from 'react-router'

const STARTER_KEYS = ['pulseStatus', 'diagnosePulse', 'syncHelp', 'panelUrl', 'importProxyLink'] as const
const GROQ_API_KEYS_URL = 'https://console.groq.com/keys'

type ChatEntry = CopilotMessage & { id: string }

function CopilotSetupHelp() {
  const { t } = useTranslation()

  return (
    <div className="bg-muted/60 space-y-2 rounded-lg border p-3 text-sm">
      <p className="font-medium">{t('copilot.setupTitle')}</p>
      <p className="text-muted-foreground text-xs leading-relaxed">{t('copilot.setupIntro')}</p>
      <a
        href={GROQ_API_KEYS_URL}
        target="_blank"
        rel="noopener noreferrer"
        className="text-primary inline-flex items-center gap-1.5 text-xs font-medium hover:underline"
      >
        {t('copilot.getApiKey')}
        <ExternalLink className="h-3.5 w-3.5 shrink-0" />
      </a>
      <pre
        className="bg-background text-muted-foreground overflow-x-auto rounded-md border p-2 font-mono text-[10px] leading-relaxed"
        dir="ltr"
      >
        {`COPILOT_ENABLED=true
COPILOT_PROVIDER=groq
OPENAI_API_KEY=gsk_...
COPILOT_MODEL=openai/gpt-oss-20b`}
      </pre>
      <p className="text-muted-foreground text-[11px]">{t('copilot.setupRestart')}</p>
    </div>
  )
}

function newId() {
  return `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`
}

export type CopilotSheetProps = {
  open: boolean
  onOpenChange: (open: boolean) => void
  configured: boolean
}

export function CopilotSheet({ open, onOpenChange, configured }: CopilotSheetProps) {
  const { t, i18n } = useTranslation()
  const location = useLocation()
  const pagePath = location.pathname
  const [messages, setMessages] = useState<ChatEntry[]>([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const bottomRef = useRef<HTMLDivElement>(null)
  const isRtl = i18n.dir() === 'rtl'

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, loading])

  useEffect(() => {
    if (!open) return
    setError(null)
  }, [open])

  const send = useCallback(
    async (text: string) => {
      const trimmed = text.trim()
      if (!trimmed || loading) return

      const userMsg: ChatEntry = { id: newId(), role: 'user', content: trimmed }
      const nextMessages = [...messages, userMsg]
      setMessages(nextMessages)
      setInput('')
      setLoading(true)
      setError(null)

      try {
        const payload = nextMessages.map(({ role, content }) => ({ role, content }))
        const response = await sendCopilotChat({ messages: payload, page_path: pagePath })
        setMessages(prev => [
          ...prev,
          { id: newId(), role: 'assistant', content: response.reply },
        ])
      } catch (e: unknown) {
        const detail =
          (e as { data?: { detail?: string } })?.data?.detail ||
          (e as Error)?.message ||
          t('copilot.sendError')
        setError(String(detail))
      } finally {
        setLoading(false)
      }
    },
    [loading, messages, pagePath, t],
  )

  const onSubmit = (event: React.FormEvent) => {
    event.preventDefault()
    void send(input)
  }

  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent
        side={isRtl ? 'left' : 'right'}
        className={cn('flex h-full w-full flex-col gap-0 overflow-hidden p-0 sm:max-w-md')}
        onOpenAutoFocus={e => e.preventDefault()}
      >
        <SheetHeader className="border-b px-4 py-4 pe-12 text-start">
          <SheetTitle className="flex items-center gap-2">
            <Sparkles className="text-primary h-5 w-5" />
            {t('copilot.title')}
          </SheetTitle>
          <SheetDescription className="text-start">
            {configured ? t('copilot.description') : t('copilot.notConfigured')}
          </SheetDescription>
          {!configured && <CopilotSetupHelp />}
          <p className="text-muted-foreground font-mono text-[10px] tracking-wide uppercase">
            {t('copilot.context')}: {pagePath}
          </p>
        </SheetHeader>

        <ScrollArea className="min-h-0 flex-1 px-4 py-3">
          {messages.length === 0 && (
            <div className="space-y-3 py-2">
              <p className="text-muted-foreground text-sm">{t('copilot.emptyHint')}</p>
              <div className="flex flex-wrap gap-2">
                {STARTER_KEYS.map(key => (
                  <Button
                    key={key}
                    type="button"
                    variant="outline"
                    size="sm"
                    className="h-auto whitespace-normal text-start"
                    disabled={!configured || loading}
                    onClick={() => void send(t(`copilot.starters.${key}`))}
                  >
                    {t(`copilot.starters.${key}`)}
                  </Button>
                ))}
              </div>
            </div>
          )}

          <div className="space-y-3 pb-4">
            {messages.map(msg => (
              <div
                key={msg.id}
                className={cn('flex gap-2', msg.role === 'user' ? 'justify-end' : 'justify-start')}
              >
                {msg.role === 'assistant' && (
                  <div className="bg-primary/10 text-primary mt-1 flex h-7 w-7 shrink-0 items-center justify-center rounded-full">
                    <Bot className="h-4 w-4" />
                  </div>
                )}
                <div
                  className={cn(
                    'max-w-[85%] rounded-2xl px-3 py-2 text-sm leading-relaxed whitespace-pre-wrap',
                    msg.role === 'user'
                      ? 'bg-primary text-primary-foreground rounded-br-sm'
                      : 'bg-muted rounded-bl-sm',
                  )}
                >
                  {msg.content}
                </div>
                {msg.role === 'user' && (
                  <div className="bg-muted mt-1 flex h-7 w-7 shrink-0 items-center justify-center rounded-full">
                    <User className="h-4 w-4" />
                  </div>
                )}
              </div>
            ))}
            {loading && (
              <div className="text-muted-foreground flex items-center gap-2 text-sm">
                <Loader2 className="h-4 w-4 animate-spin" />
                {t('copilot.thinking')}
              </div>
            )}
            <div ref={bottomRef} />
          </div>
        </ScrollArea>

        {error && (
          <div className="border-t border-destructive/30 bg-destructive/10 text-destructive px-4 py-2 text-xs">
            {error}
          </div>
        )}

        <form onSubmit={onSubmit} className="border-t p-4">
          <div className="flex items-end gap-2">
            <Textarea
              value={input}
              onChange={e => setInput(e.target.value)}
              placeholder={configured ? t('copilot.placeholder') : t('copilot.notConfigured')}
              disabled={!configured || loading}
              rows={2}
              className="min-h-[72px] resize-none"
              onKeyDown={e => {
                if (e.key === 'Enter' && !e.shiftKey) {
                  e.preventDefault()
                  void send(input)
                }
              }}
            />
            <Button type="submit" size="icon" disabled={!configured || loading || !input.trim()}>
              <Send className="h-4 w-4" />
            </Button>
          </div>
        </form>
      </SheetContent>
    </Sheet>
  )
}
