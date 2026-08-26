import { z } from 'zod'
import type { HpxTunnelResponse, HpxTunnelRole } from '@/service/api/hpx-tunnels'

export const portForwardSchema = z.object({
  external_port: z.coerce.number().int().min(1).max(65535),
  internal_ip: z.string().min(7).max(45),
  internal_port: z.coerce.number().int().min(1).max(65535),
})

export const hpxTunnelFormSchema = z
  .object({
    name: z.string().min(1).max(128),
    role: z.enum(['iran', 'foreign'] as const),
    password: z.string().min(4).max(128).optional(),
    enabled: z.boolean(),
    remote_ip: z.string().max(45).optional().nullable(),
    server_listen: z.string().max(45).default('0.0.0.0'),
    interface: z.string().max(32).default('hpx0'),
    local_ip: z.string().max(45).default('10.200.200.2'),
    subnet: z.string().max(64).default('10.200.200.0/24'),
    mtu: z.coerce.number().int().min(576).max(9000).nullable().optional(),
    keepalive: z.coerce.number().int().min(1).max(300).default(5),
    dscp_mark: z.coerce.number().int().min(0).max(63).nullable().optional(),
    bandwidth_limit: z.string().max(32).optional().nullable(),
    operating_mode: z.string().max(64).optional().nullable(),
    port_forwards: z.array(portForwardSchema).default([]),
    docker_image: z.string().max(128).default('hpx-icmp:0.0.3'),
    backup_tunnel_id: z.coerce.number().int().positive().nullable().optional(),
    auto_failover: z.boolean().default(false),
    priority: z.coerce.number().int().min(0).max(100).default(0),
    alert_on_down: z.boolean().default(true),
    note: z.string().max(512).optional().nullable(),
    start_after_create: z.boolean().default(true),
  })
  .superRefine((values, ctx) => {
    if (values.role === 'iran' && !values.remote_ip) {
      ctx.addIssue({ code: 'custom', message: 'remote_ip required', path: ['remote_ip'] })
    }
  })

export type HpxTunnelFormValues = z.infer<typeof hpxTunnelFormSchema>

export const hpxTunnelFormDefaultValues = (role: HpxTunnelRole = 'iran'): HpxTunnelFormValues => ({
  name: '',
  role,
  password: '',
  enabled: true,
  remote_ip: '',
  server_listen: '0.0.0.0',
  interface: 'hpx0',
  local_ip: role === 'foreign' ? '10.200.200.1' : '10.200.200.2',
  subnet: '10.200.200.0/24',
  mtu: 1200,
  keepalive: 5,
  dscp_mark: null,
  bandwidth_limit: null,
  operating_mode: null,
  port_forwards: [],
  docker_image: 'hpx-icmp:0.0.3',
  backup_tunnel_id: null,
  auto_failover: false,
  priority: 0,
  alert_on_down: true,
  note: '',
  start_after_create: true,
})

export const hpxTunnelFormFromResponse = (tunnel: HpxTunnelResponse): HpxTunnelFormValues => ({
  name: tunnel.name,
  role: tunnel.role,
  password: '',
  enabled: tunnel.enabled,
  remote_ip: tunnel.remote_ip ?? '',
  server_listen: tunnel.server_listen,
  interface: tunnel.interface,
  local_ip: tunnel.local_ip,
  subnet: tunnel.subnet,
  mtu: tunnel.mtu ?? 1200,
  keepalive: tunnel.keepalive,
  dscp_mark: tunnel.dscp_mark ?? null,
  bandwidth_limit: tunnel.bandwidth_limit ?? null,
  operating_mode: tunnel.operating_mode ?? null,
  port_forwards: tunnel.port_forwards ?? [],
  docker_image: tunnel.docker_image,
  backup_tunnel_id: tunnel.backup_tunnel_id ?? null,
  auto_failover: tunnel.auto_failover,
  priority: tunnel.priority,
  alert_on_down: tunnel.alert_on_down,
  note: tunnel.note ?? '',
  start_after_create: false,
})

export const hpxTunnelFormToCreatePayload = (values: HpxTunnelFormValues) => ({
  ...values,
  remote_ip: values.remote_ip || null,
  note: values.note || null,
  bandwidth_limit: values.bandwidth_limit || null,
  operating_mode: values.operating_mode || null,
  password: values.password || '',
})

export const hpxTunnelFormToUpdatePayload = (values: HpxTunnelFormValues) => {
  const payload = hpxTunnelFormToCreatePayload(values)
  if (!payload.password) delete (payload as { password?: string }).password
  delete (payload as { start_after_create?: boolean }).start_after_create
  return payload
}
