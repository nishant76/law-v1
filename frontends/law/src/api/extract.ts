import api from './client'
import { useAuthStore } from '@/store/authStore'
import type { ApiResponse, UniversalExtraction } from '@/types'

export const extractDocument = (document_id: string) =>
  api.post<ApiResponse<UniversalExtraction>>('/extract', { document_id })

export const extractFromUpload = (file: File) => {
  const form = new FormData()
  form.append('file', file)
  return api.post<ApiResponse<UniversalExtraction>>('/extract/upload', form, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
}

// ── Streaming upload — connects to /extract/upload/stream SSE endpoint ────────
// Calls onToken for each text chunk, onProgress for stage updates,
// onResult when the full structured extraction is ready, onError on failure.

export const streamExtractUpload = async (
  file: File,
  onToken: (text: string) => void,
  onProgress: (stage: string, pct?: number, message?: string) => void,
  onResult: (data: UniversalExtraction, rawText?: string) => void,
  onError: (code: string, message: string) => void,
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
      // Tell the backend NOT to gzip this response.
      // GZipMiddleware buffers the entire stream before compressing,
      // which makes the browser wait for the full response before
      // delivering any data — killing the streaming effect entirely.
      'Accept-Encoding': 'identity',
    },
    body: form,
  })

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

    // SSE events are separated by double newlines
    const events = buffer.split('\n\n')
    buffer = events.pop() ?? ''   // keep incomplete trailing chunk

    for (const raw of events) {
      const line = raw.trim()
      if (!line.startsWith('data:')) continue
      try {
        const payload = JSON.parse(line.slice(5).trim())
        if (payload.type === 'token')    onToken(payload.text ?? '')
        if (payload.type === 'progress') onProgress(payload.stage, payload.pct, payload.message)
        if (payload.type === 'result')   onResult(payload.data, payload.raw_text)
        if (payload.type === 'error')    onError(payload.code ?? 'error', payload.message ?? 'Unknown error')
        if (payload.type === 'done')     return
      } catch {
        // malformed SSE line — skip
      }
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
