import api from './client'
import type { ApiResponse, AuthTokens, User } from '@/types'

export const login = (email: string, password: string) =>
  api.post<ApiResponse<{ access_token: string; user: User }>>('/auth/login', { email, password })

export const logout = () => api.post<ApiResponse>('/auth/logout')

export const refreshToken = () =>
  api.post<ApiResponse<AuthTokens>>('/auth/refresh', {}, { withCredentials: true })

export const changePassword = (current_password: string, new_password: string) =>
  api.post<ApiResponse>('/auth/change-password', { current_password, new_password })

export const acceptInvite = (token: string, full_name: string, password: string) =>
  api.post<ApiResponse<{ access_token: string; user: User }>>('/auth/accept-invite', {
    token, full_name, password,
  })
