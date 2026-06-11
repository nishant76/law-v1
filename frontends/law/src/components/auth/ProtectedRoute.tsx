import { Navigate, useLocation } from 'react-router-dom'
import { useAuthStore } from '@/store/authStore'

interface Props { children: React.ReactNode }

/** Returns true if the JWT access token is expired (or unparseable). */
function isTokenExpired(token: string): boolean {
  try {
    const payload = JSON.parse(atob(token.split('.')[1]))
    // exp is in seconds; add 10s buffer for clock skew
    return Date.now() / 1000 > payload.exp - 10
  } catch {
    return true
  }
}

export default function ProtectedRoute({ children }: Props) {
  const { isAuthenticated, accessToken, logout } = useAuthStore()
  const location = useLocation()

  if (!isAuthenticated()) {
    return <Navigate to="/login" state={{ from: location }} replace />
  }

  // Token present but expired → clear auth and send to login
  if (accessToken && isTokenExpired(accessToken)) {
    logout()
    return <Navigate to="/login" state={{ from: location, sessionExpired: true }} replace />
  }

  return <>{children}</>
}
