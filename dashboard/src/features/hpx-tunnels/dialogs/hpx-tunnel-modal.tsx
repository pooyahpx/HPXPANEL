import { Accordion, AccordionContent, AccordionItem, AccordionTrigger } from '@/components/ui/accordion'
import { Button } from '@/components/ui/button'
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { Form, FormControl, FormField, FormItem, FormLabel, FormMessage } from '@/components/ui/form'
import { Input } from '@/components/ui/input'
import { LoaderButton } from '@/components/ui/loader-button'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Switch } from '@/components/ui/switch'
import { Textarea } from '@/components/ui/textarea'
import useDirDetection from '@/hooks/use-dir-detection'
import useDynamicErrorHandler from '@/hooks/use-dynamic-errors'
import {
  hpxTunnelFormDefaultValues,
  hpxTunnelFormToCreatePayload,
  hpxTunnelFormToUpdatePayload,
  type HpxTunnelFormValues,
} from '@/features/hpx-tunnels/forms/hpx-tunnel-form'
import { type HpxTunnelResponse, useCreateHpxTunnel, useUpdateHpxTunnel } from '@/service/api/hpx-tunnels'
import { cn } from '@/lib/utils'
import { Plus, Trash2 } from 'lucide-react'
import { UseFormReturn } from 'react-hook-form'
import { useTranslation } from 'react-i18next'
import { toast } from 'sonner'

interface HpxTunnelModalProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  form: UseFormReturn<HpxTunnelFormValues>
  editingTunnel: HpxTunnelResponse | null
  onSuccess?: () => void
}

export default function HpxTunnelModal({ open, onOpenChange, form, editingTunnel, onSuccess }: HpxTunnelModalProps) {
  const { t } = useTranslation()
  const dir = useDirDetection()
  const handleError = useDynamicErrorHandler()
  const createMutation = useCreateHpxTunnel()
  const updateMutation = useUpdateHpxTunnel()
  const isEditing = !!editingTunnel
  const role = form.watch('role')

  const onSubmit = async (values: HpxTunnelFormValues) => {
    try {
      if (isEditing && editingTunnel) {
        await updateMutation.mutateAsync({ id: editingTunnel.id, data: hpxTunnelFormToUpdatePayload(values) })
        toast.success(t('success', { defaultValue: 'Success' }), {
          description: t('hpxTunnel.updateSuccess', { defaultValue: 'Tunnel updated.' }),
        })
      } else {
        const result = await createMutation.mutateAsync(hpxTunnelFormToCreatePayload(values) as any)
        toast.success(t('success', { defaultValue: 'Success' }), {
          description: result.message || t('hpxTunnel.createSuccess', { defaultValue: 'Tunnel created.' }),
        })
      }
      onOpenChange(false)
      onSuccess?.()
    } catch (error) {
      handleError(error)
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent dir={dir} className={cn('max-h-[90vh] overflow-y-auto sm:max-w-2xl', dir === 'rtl' && 'text-right')}>
        <DialogHeader>
          <DialogTitle>{isEditing ? t('hpxTunnel.editTunnel', { defaultValue: 'Edit tunnel' }) : t('hpxTunnel.addTunnel', { defaultValue: 'Add tunnel' })}</DialogTitle>
          <DialogDescription>
            {t('hpxTunnel.modalDescription', {
              defaultValue: 'Configure ChaCha20-encrypted ICMP tunnel. IRAN connects to a remote FOREIGN server.',
            })}
          </DialogDescription>
        </DialogHeader>

        <Form {...form}>
          <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-4">
            <div className="grid gap-4 sm:grid-cols-2">
              <FormField
                control={form.control}
                name="name"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>{t('name', { defaultValue: 'Name' })}</FormLabel>
                    <FormControl>
                      <Input {...field} />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
              <FormField
                control={form.control}
                name="role"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>{t('hpxTunnel.role.label', { defaultValue: 'Role' })}</FormLabel>
                    <Select
                      value={field.value}
                      onValueChange={value => {
                        field.onChange(value)
                        form.setValue('local_ip', value === 'foreign' ? '10.200.200.1' : '10.200.200.2')
                      }}
                    >
                      <FormControl>
                        <SelectTrigger>
                          <SelectValue />
                        </SelectTrigger>
                      </FormControl>
                      <SelectContent>
                        <SelectItem value="iran">{t('hpxTunnel.role.iran', { defaultValue: 'IRAN (client)' })}</SelectItem>
                        <SelectItem value="foreign">{t('hpxTunnel.role.foreign', { defaultValue: 'FOREIGN (server)' })}</SelectItem>
                      </SelectContent>
                    </Select>
                    <FormMessage />
                  </FormItem>
                )}
              />
            </div>

            <FormField
              control={form.control}
              name="password"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>{t('password', { defaultValue: 'Password' })}</FormLabel>
                  <FormControl>
                    <Input {...field} type="password" placeholder={isEditing ? t('hpxTunnel.passwordKeep', { defaultValue: 'Leave blank to keep current' }) : ''} />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />

            {role === 'iran' ? (
              <FormField
                control={form.control}
                name="remote_ip"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>{t('hpxTunnel.remoteIp', { defaultValue: 'Remote IP (FOREIGN server)' })}</FormLabel>
                    <FormControl>
                      <Input {...field} value={field.value ?? ''} dir="ltr" className="font-mono" />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
            ) : (
              <FormField
                control={form.control}
                name="server_listen"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>{t('hpxTunnel.serverListen', { defaultValue: 'Listen address' })}</FormLabel>
                    <FormControl>
                      <Input {...field} dir="ltr" className="font-mono" />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
            )}

            <Accordion type="single" collapsible defaultValue="network">
              <AccordionItem value="network">
                <AccordionTrigger>{t('hpxTunnel.section.network', { defaultValue: 'Network' })}</AccordionTrigger>
                <AccordionContent className="grid gap-4 sm:grid-cols-2">
                  <FormField control={form.control} name="interface" render={({ field }) => (
                    <FormItem><FormLabel>{t('hpxTunnel.interface', { defaultValue: 'Interface' })}</FormLabel><FormControl><Input {...field} dir="ltr" className="font-mono" /></FormControl><FormMessage /></FormItem>
                  )} />
                  <FormField control={form.control} name="local_ip" render={({ field }) => (
                    <FormItem><FormLabel>{t('hpxTunnel.localIp', { defaultValue: 'Local IP' })}</FormLabel><FormControl><Input {...field} dir="ltr" className="font-mono" /></FormControl><FormMessage /></FormItem>
                  )} />
                  <FormField control={form.control} name="subnet" render={({ field }) => (
                    <FormItem><FormLabel>{t('hpxTunnel.subnet', { defaultValue: 'Subnet' })}</FormLabel><FormControl><Input {...field} dir="ltr" className="font-mono" /></FormControl><FormMessage /></FormItem>
                  )} />
                  <FormField control={form.control} name="mtu" render={({ field }) => (
                    <FormItem><FormLabel>MTU</FormLabel><FormControl><Input {...field} value={field.value ?? ''} type="number" /></FormControl><FormMessage /></FormItem>
                  )} />
                  <FormField control={form.control} name="keepalive" render={({ field }) => (
                    <FormItem><FormLabel>{t('hpxTunnel.keepalive', { defaultValue: 'Keepalive (s)' })}</FormLabel><FormControl><Input {...field} type="number" /></FormControl><FormMessage /></FormItem>
                  )} />
                  {role === 'iran' ? (
                    <FormField control={form.control} name="dscp_mark" render={({ field }) => (
                      <FormItem><FormLabel>DSCP</FormLabel><FormControl><Input {...field} value={field.value ?? ''} type="number" /></FormControl><FormMessage /></FormItem>
                    )} />
                  ) : (
                    <FormField control={form.control} name="bandwidth_limit" render={({ field }) => (
                      <FormItem><FormLabel>{t('hpxTunnel.bandwidthLimit', { defaultValue: 'Bandwidth limit' })}</FormLabel><FormControl><Input {...field} value={field.value ?? ''} placeholder="50mbit" /></FormControl><FormMessage /></FormItem>
                    )} />
                  )}
                </AccordionContent>
              </AccordionItem>

              <AccordionItem value="advanced">
                <AccordionTrigger>{t('hpxTunnel.section.advanced', { defaultValue: 'Advanced & failover' })}</AccordionTrigger>
                <AccordionContent className="space-y-4">
                  <div className="grid gap-4 sm:grid-cols-2">
                    <FormField control={form.control} name="priority" render={({ field }) => (
                      <FormItem><FormLabel>{t('hpxTunnel.priority', { defaultValue: 'Priority' })}</FormLabel><FormControl><Input {...field} type="number" /></FormControl><FormMessage /></FormItem>
                    )} />
                    <FormField control={form.control} name="backup_tunnel_id" render={({ field }) => (
                      <FormItem><FormLabel>{t('hpxTunnel.backupTunnelId', { defaultValue: 'Backup tunnel ID' })}</FormLabel><FormControl><Input {...field} value={field.value ?? ''} type="number" /></FormControl><FormMessage /></FormItem>
                    )} />
                  </div>
                  <div className="flex flex-wrap gap-6">
                    <FormField control={form.control} name="auto_failover" render={({ field }) => (
                      <FormItem className="flex items-center gap-2 space-y-0"><FormControl><Switch checked={field.value} onCheckedChange={field.onChange} /></FormControl><FormLabel>{t('hpxTunnel.failoverEnabled', { defaultValue: 'Auto-failover' })}</FormLabel></FormItem>
                    )} />
                    <FormField control={form.control} name="alert_on_down" render={({ field }) => (
                      <FormItem className="flex items-center gap-2 space-y-0"><FormControl><Switch checked={field.value} onCheckedChange={field.onChange} /></FormControl><FormLabel>{t('hpxTunnel.alertOnDown', { defaultValue: 'Telegram alert on down' })}</FormLabel></FormItem>
                    )} />
                    {!isEditing && (
                      <FormField control={form.control} name="start_after_create" render={({ field }) => (
                        <FormItem className="flex items-center gap-2 space-y-0"><FormControl><Switch checked={field.value} onCheckedChange={field.onChange} /></FormControl><FormLabel>{t('hpxTunnel.startAfterCreate', { defaultValue: 'Start after create' })}</FormLabel></FormItem>
                      )} />
                    )}
                  </div>
                  <FormField control={form.control} name="note" render={({ field }) => (
                    <FormItem><FormLabel>{t('note', { defaultValue: 'Note' })}</FormLabel><FormControl><Textarea {...field} value={field.value ?? ''} rows={2} /></FormControl><FormMessage /></FormItem>
                  )} />
                </AccordionContent>
              </AccordionItem>

              {role === 'iran' && (
                <AccordionItem value="ports">
                  <AccordionTrigger>{t('hpxTunnel.section.portForwards', { defaultValue: 'Port forwarding' })}</AccordionTrigger>
                  <AccordionContent className="space-y-3">
                    {form.watch('port_forwards').map((_, index) => (
                      <div key={index} className="grid gap-2 rounded-lg border p-3 sm:grid-cols-4">
                        <FormField control={form.control} name={`port_forwards.${index}.external_port`} render={({ field }) => (
                          <FormItem><FormLabel>{t('hpxTunnel.externalPort', { defaultValue: 'External' })}</FormLabel><FormControl><Input {...field} type="number" /></FormControl></FormItem>
                        )} />
                        <FormField control={form.control} name={`port_forwards.${index}.internal_ip`} render={({ field }) => (
                          <FormItem><FormLabel>{t('hpxTunnel.internalIp', { defaultValue: 'Internal IP' })}</FormLabel><FormControl><Input {...field} dir="ltr" className="font-mono" /></FormControl></FormItem>
                        )} />
                        <FormField control={form.control} name={`port_forwards.${index}.internal_port`} render={({ field }) => (
                          <FormItem><FormLabel>{t('hpxTunnel.internalPort', { defaultValue: 'Internal port' })}</FormLabel><FormControl><Input {...field} type="number" /></FormControl></FormItem>
                        )} />
                        <div className="flex items-end">
                          <Button type="button" variant="ghost" size="icon" onClick={() => {
                            const current = form.getValues('port_forwards')
                            form.setValue('port_forwards', current.filter((_, i) => i !== index))
                          }}>
                            <Trash2 className="size-4" />
                          </Button>
                        </div>
                      </div>
                    ))}
                    <Button
                      type="button"
                      variant="outline"
                      size="sm"
                      onClick={() => form.setValue('port_forwards', [...form.getValues('port_forwards'), { external_port: 443, internal_ip: '10.200.200.1', internal_port: 443 }])}
                    >
                      <Plus className="size-4" />
                      {t('hpxTunnel.addPortForward', { defaultValue: 'Add rule' })}
                    </Button>
                  </AccordionContent>
                </AccordionItem>
              )}
            </Accordion>

            <div className="flex justify-end gap-2 pt-2">
              <Button type="button" variant="outline" onClick={() => onOpenChange(false)}>
                {t('cancel', { defaultValue: 'Cancel' })}
              </Button>
              <LoaderButton type="submit" loading={createMutation.isPending || updateMutation.isPending}>
                {isEditing ? t('save', { defaultValue: 'Save' }) : t('create', { defaultValue: 'Create' })}
              </LoaderButton>
            </div>
          </form>
        </Form>
      </DialogContent>
    </Dialog>
  )
}
