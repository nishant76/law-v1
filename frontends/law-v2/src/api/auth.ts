import api from './client'
import type { ApiResponse, AuthTokens, User } from '@/types'

export const login = (email: string, password: string) =>
  api.post<ApiResponse<{ access_token: string; user: User }>>('/auth/login', { email, password })

export const register = (firm_name: string, email: string, password: string) =>
  api.post<{ success: boolean; message: string; data: { firm_id: string; user_id: string } | null }>(
    '/auth/register',
    { firm_name, email, password, plan: 'trial' }
  )

export const logout = () => api.post<ApiResponse>('/auth/logout')

export const refreshToken = () =>
  api.post<ApiResponse<AuthTokens>>('/auth/refresh', {}, { withCredentials: true })

export const changePassword = (current_password: string, new_password: string) =>
  api.post<ApiResponse>('/auth/change-password', { current_password, new_password })
