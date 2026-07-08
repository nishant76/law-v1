import api from './client'
import { useAuthStore } from '@/store/authStore'
import type { ApiResponse } from '@/types'

export interface StreamResult {
  document_id: string
}

export const streamExtractUpload = async (
  file: File,
  onToken: (text: string) => void,
  onProgress: (stage: string) => void,
  onResult: (result: StreamResult) => void,
  onError: (code: string, message: string) => void,
  onDocumentReady?: (document_id: string) => void,
): Promise<void> => {
  const form = new FormData()
  form.append('file', file)

  const base = import.meta.env.VITE_API_URL
    ? `${import.meta.env.VITE_API_URL}/api/v1`
    : '/api/v1'
  const token = useAuthStore.getState().accessToken

  const response = await fetch(`${base}/extract/upload/stream`, {
    method: 'POST',
    headers: {
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      'Accept-Encoding': 'identity',
    },
    body: form,
  })

  if (response.status === 401) {
    useAuthStore.getState().logout()
    window.location.href = '/auth'
    return
  }

  if (!response.ok || !response.body) {
    onError('network_error', `Request failed (${response.status})`)
    return
  }

  const reader = response.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''

  while (true) {
    const { done, value } = await reader.read()
    if (done) break
    buffer += decoder.decode(value, { stream: true })
    const events = buffer.split('\n\n')
    buffer = events.pop() ?? ''
    for (const raw of events) {
      const line = raw.trim()
      if (!line.startsWith('data:')) continue
      try {
        const payload = JSON.parse(line.slice(5).trim())
        if (payload.type === 'token')           onToken(payload.text ?? '')
        if (payload.type === 'progress')        onProgress(payload.stage)
        if (payload.type === 'document_ready')  onDocumentReady?.(payload.document_id ?? 'direct')
        if (payload.type === 'result')          onResult({ document_id: payload.document_id ?? 'direct' })
        if (payload.type === 'error')           onError(payload.code ?? 'error', payload.message ?? 'Unknown error')
        if (payload.type === 'done')            return
      } catch { /* malformed SSE line */ }
    }
  }
}

export const chatWithDocument = (
  document_id: string,
  messages: Array<{ role: 'user' | 'assistant'; content: string }>
) =>
  api.post<ApiResponse<{ answer: string; confidence: number; sources: unknown[] }>>('/extract/chat', {
    document_id,
    messages,
  })

export const streamChatWithDocument = async (
  document_id: string,
  messages: Array<{ role: 'user' | 'assistant'; content: string }>,
  onToken: (text: string) => void,
  onDone: () => void,
  onError: (message: string) => void,
): Promise<void> => {
  const base = import.meta.env.VITE_API_URL
    ? `${import.meta.env.VITE_API_URL}/api/v1`
    : '/api/v1'
  const token = useAuthStore.getState().accessToken

  const response = await fetch(`${base}/extract/chat/stream`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Accept-Encoding': 'identity',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    body: JSON.stringify({ document_id, messages }),
  })

  if (!response.ok || !response.body) {
    onError(`Request failed (${response.status})`)
    return
  }

  const reader = response.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''

  while (true) {
    const { done, value } = await reader.read()
    if (done) break
    buffer += decoder.decode(value, { stream: true })
    const events = buffer.split('\n\n')
    buffer = events.pop() ?? ''
    for (const raw of events) {
      const line = raw.trim()
      if (!line.startsWith('data:')) continue
      try {
        const payload = JSON.parse(line.slice(5).trim())
        if (payload.type === 'token') onToken(payload.text ?? '')
        if (payload.type === 'done')  { onDone(); return }
        if (payload.type === 'error') { onError(payload.message ?? 'Unknown error'); return }
      } catch { /* malformed SSE line */ }
    }
  }
}
