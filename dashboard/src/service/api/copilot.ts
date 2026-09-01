import { fetcher } from '@/service/http'

export type CopilotRole = 'user' | 'assistant' | 'system'

export interface CopilotMessage {
  role: CopilotRole
  content: string
}

export interface CopilotChatRequest {
  messages: CopilotMessage[]
  page_path?: string | null
}

export interface CopilotChatResponse {
  reply: string
  actions_taken: string[]
}

export interface CopilotStatusResponse {
  enabled: boolean
  configured: boolean
  model: string
}

const BASE = '/api/copilot'

export const getCopilotStatus = () => fetcher<CopilotStatusResponse>(`${BASE}/status`)

export const sendCopilotChat = (data: CopilotChatRequest) =>
  fetcher<CopilotChatResponse>(`${BASE}/chat`, { method: 'POST', body: data })

export const getCopilotStatusQueryKey = () => ['copilot-status'] as const
