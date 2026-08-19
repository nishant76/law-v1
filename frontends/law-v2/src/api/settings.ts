import api from './client'
import type { ApiResponse } from '@/types'

export interface AdvocateProfile {
  user: {
    id: string
    name: string
    email: string
    phone: string | null
    role: string
    bar_council_number: string | null
    ecourts_advocate_name: string | null
    ecourts_state_code: string | null
    whatsapp_number: string | null
    daily_cause_list_enabled: boolean
  }
  firm: {
    name: string | null
    city: string | null
    state: string | null
    plan: string | null
  }
  /** What the server can actually deliver — the page must not claim more. */
  capabilities: {
    email_configured: boolean
    whatsapp_configured: boolean
    ecourts_configured: boolean
    reminder_offsets_days: number[]
    timezone: string
  }
}

export type ProfileUpdate = Partial<{
  name: string
  phone: string
  bar_council_number: string
  ecourts_advocate_name: string
  ecourts_state_code: string
  whatsapp_number: string
  daily_cause_list_enabled: boolean
  firm_name: string
  firm_city: string
  firm_state: string
}>

export const getProfile = () =>
  api.get<ApiResponse<AdvocateProfile>>('/settings/profile')

export const updateProfile = (body: ProfileUpdate) =>
  api.patch<ApiResponse<AdvocateProfile>>('/settings/profile', body)
