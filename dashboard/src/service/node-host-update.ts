import { orvalFetcher } from './http'

export type NodeHostUpdatePayload = {
  ssh_username: string
  ssh_port: number
  ssh_password?: string
  ssh_private_key?: string
}

export type NodeHostUpdateResult = {
  detail: string
  log?: string
}

/** SSH into the node host and run hpx-node update (installs serviced + pulls image). */
export function hostUpdateNode(nodeId: number, data: NodeHostUpdatePayload, signal?: AbortSignal) {
  return orvalFetcher<NodeHostUpdateResult>({
    url: `/api/node/${nodeId}/host_update`,
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    data,
    signal,
  })
}
