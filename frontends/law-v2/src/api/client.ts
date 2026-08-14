import axios from 'axios'
import { useAuthStore } from '@/store/authStore'

// Opt-out flag for background/advisory calls (e.g. the live brief-strength check): on a 401
// that can't be refreshed, reject silently instead of logging the user out and redirecting.
declare module 'axios' {
  export interface AxiosRequestConfig {
    skipAuthRedirect?: boolean
  }
}

const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL
    ? `${import.meta.env.VITE_API_URL}/api/v1`
    : '/api/v1',
  timeout: 120000,
  headers: { 'Content-Type': 'application/json' },
})

api.interceptors.request.use((config) => {
  const token = useAuthStore.getState().accessToken
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

api.interceptors.response.use(
  (res) => res,
  async (error) => {
    const original = error.config
    if (error.response?.status === 401 && !original._retry) {
      original._retry = true
      try {
        const { data } = await axios.post('/api/v1/auth/refresh', {}, { withCredentials: true })
        useAuthStore.getState().setTokens(data.data.access_token)
        original.headers.Authorization = `Bearer ${data.data.access_token}`
        return api(original)
      } catch {
        if (!original.skipAuthRedirect) {
          useAuthStore.getState().logout()
          window.location.href = '/auth'
        }
      }
    }
    return Promise.reject(error)
  }
)

export default api
