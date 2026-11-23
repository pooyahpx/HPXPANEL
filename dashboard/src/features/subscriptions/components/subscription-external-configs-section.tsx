import type { SubscriptionFormData } from '@/features/subscriptions/components/subscription-settings-schema'
import { Button } from '@/components/ui/button'
import { FormControl, FormDescription, FormField, FormItem, FormLabel, FormMessage } from '@/components/ui/form'
import { Input } from '@/components/ui/input'
import { Switch } from '@/components/ui/switch'
import { Textarea } from '@/components/ui/textarea'
import { Plus, Trash2, Link2 } from 'lucide-react'
import { UseFormReturn, useFieldArray } from 'react-hook-form'
import { useTranslation } from 'react-i18next'

export interface SubscriptionExternalConfigsSectionProps {
  form: UseFormReturn<SubscriptionFormData>
}

export function SubscriptionExternalConfigsSection({ form }: SubscriptionExternalConfigsSectionProps) {
  const { t } = useTranslation()
  const { fields, append, remove } = useFieldArray({
    control: form.control,
    name: 'external_configs',
  })

  return (
    <div className="space-y-3">
      <div className="flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
        <div className="space-y-1">
          <h3 className="flex items-center gap-2 text-base font-semibold sm:text-lg">
            <Link2 className="size-4 shrink-0" />
            {t('settings.subscriptions.externalConfigs.title', { defaultValue: 'Mother / external configs' })}
          </h3>
          <p className="text-muted-foreground text-xs sm:text-sm">
            {t('settings.subscriptions.externalConfigs.description', {
              defaultValue:
                'Paste share links from another panel/IP. They are appended to every user subscription (links / base64) without creating inbounds here.',
            })}
          </p>
        </div>
        <Button
          type="button"
          variant="outline"
          size="sm"
          className="cursor-pointer shrink-0"
          onClick={() => append({ name: '', link: '', enabled: true })}
        >
          <Plus className="size-4" />
          {t('settings.subscriptions.externalConfigs.add', { defaultValue: 'Add config' })}
        </Button>
      </div>

      {fields.length === 0 ? (
        <p className="text-muted-foreground rounded-lg border border-dashed px-3 py-4 text-xs sm:text-sm">
          {t('settings.subscriptions.externalConfigs.empty', {
            defaultValue: 'No external configs yet. Add a vless:// / vmess:// / trojan:// link to inject into user subs.',
          })}
        </p>
      ) : (
        <div className="space-y-3">
          {fields.map((field, index) => (
            <div key={field.id} className="bg-muted/20 space-y-3 rounded-xl border p-3 sm:p-4">
              <div className="flex items-center justify-between gap-2">
                <FormField
                  control={form.control}
                  name={`external_configs.${index}.enabled`}
                  render={({ field: switchField }) => (
                    <FormItem className="flex flex-row items-center gap-2 space-y-0">
                      <FormControl>
                        <Switch checked={switchField.value} onCheckedChange={switchField.onChange} className="cursor-pointer" />
                      </FormControl>
                      <FormLabel className="text-xs font-medium sm:text-sm">
                        {t('settings.subscriptions.externalConfigs.enabled', { defaultValue: 'Enabled in subs' })}
                      </FormLabel>
                    </FormItem>
                  )}
                />
                <Button
                  type="button"
                  variant="ghost"
                  size="icon"
                  className="text-destructive hover:text-destructive cursor-pointer"
                  onClick={() => remove(index)}
                  aria-label={t('delete', { defaultValue: 'Delete' })}
                >
                  <Trash2 className="size-4" />
                </Button>
              </div>

              <FormField
                control={form.control}
                name={`external_configs.${index}.name`}
                render={({ field: nameField }) => (
                  <FormItem className="space-y-2">
                    <FormLabel className="text-xs sm:text-sm">
                      {t('settings.subscriptions.externalConfigs.name', { defaultValue: 'Display name' })}
                    </FormLabel>
                    <FormControl>
                      <Input
                        placeholder={t('settings.subscriptions.externalConfigs.namePlaceholder', {
                          defaultValue: 'Mother unlimited',
                        })}
                        {...nameField}
                        className="text-xs sm:text-sm"
                      />
                    </FormControl>
                    <FormDescription className="text-xs">
                      {t('settings.subscriptions.externalConfigs.nameDescription', {
                        defaultValue: 'Optional — overrides the #remark in the share link for clients.',
                      })}
                    </FormDescription>
                    <FormMessage />
                  </FormItem>
                )}
              />

              <FormField
                control={form.control}
                name={`external_configs.${index}.link`}
                render={({ field: linkField }) => (
                  <FormItem className="space-y-2">
                    <FormLabel className="text-xs sm:text-sm">
                      {t('settings.subscriptions.externalConfigs.link', { defaultValue: 'Share link' })}
                    </FormLabel>
                    <FormControl>
                      <Textarea
                        rows={3}
                        dir="ltr"
                        placeholder="vless://uuid@host:port?encryption=none&security=reality&..."
                        className="resize-y font-mono text-[11px] sm:text-xs"
                        {...linkField}
                      />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
