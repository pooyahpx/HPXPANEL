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
  provider: string
  model: string
  api_key_masked?: string
}

export interface CopilotSettingsUpdate {
  enabled?: boolean
  provider?: 'groq' | 'openai' | 'openrouter' | 'ollama'
  api_key?: string
  model?: string
  base_url?: string
}

export type CopilotSettingsResponse = CopilotStatusResponse & {
  saved: boolean
  writable: boolean
}

const BASE = '/api/copilot'

export const getCopilotStatus = () => fetcher<CopilotStatusResponse>(`${BASE}/status`)

export const updateCopilotSettings = (data: CopilotSettingsUpdate) =>
  fetcher<CopilotSettingsResponse>(`${BASE}/settings`, { method: 'PUT', body: data })

export const sendCopilotChat = (data: CopilotChatRequest) =>
  fetcher<CopilotChatResponse>(`${BASE}/chat`, { method: 'POST', body: data })

export const getCopilotStatusQueryKey = () => ['copilot-status'] as const
