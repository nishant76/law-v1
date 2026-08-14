import api from './client'
import type { ApiResponse } from '@/types'

export interface AppNotification {
  id: string
  type: 'hearing' | 'deadline' | 'deadline_missed' | 'ecourts_sync' | 'document' | 'system'
  title: string
  body: string | null
  link_path: string | null
  matter_id: string | null
  read: boolean
  created_at: string
}

export interface NotificationList {
  unread_count: number
  notifications: AppNotification[]
}

export const listNotifications = (unreadOnly = false, limit = 50) =>
  api.get<ApiResponse<NotificationList>>('/notifications', {
    params: { unread_only: unreadOnly, limit },
  })

export const markNotificationRead = (id: string) =>
  api.put<ApiResponse>(`/notifications/${id}/read`)

export const markAllNotificationsRead = () =>
  api.put<ApiResponse<{ marked: number }>>('/notifications/read-all')
