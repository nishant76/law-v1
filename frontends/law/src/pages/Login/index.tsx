import { useState } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import { useMutation } from '@tanstack/react-query'
import { login } from '@/api/auth'
import { useAuthStore } from '@/store/authStore'

export default function LoginPage() {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const { setAuth } = useAuthStore()
  const navigate = useNavigate()

  const mutation = useMutation({
    mutationFn: () => login(email, password),
    onSuccess: ({ data }) => {
      setAuth(data.data.user, data.data.access_token)
      navigate('/')
    },
    onError: (err: unknown) => {
      const msg = (err as { response?: { data?: { error?: { message?: string } } } })
        ?.response?.data?.error?.message ?? 'Invalid email or password'
      setError(msg)
    },
  })

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    if (!email || !password) { setError('Enter your email and password'); return }
    mutation.mutate()
  }

  return (
    <div className="min-h-full flex items-center justify-center bg-bg p-4">
      <div className="w-full max-w-[360px]">
        {/* Logo */}
        <div className="flex items-center justify-center gap-[9px] mb-8">
          <div className="w-8 h-8 bg-ink rounded-[8px] flex items-center justify-center flex-shrink-0">
            <svg viewBox="0 0 14 14" fill="none" className="w-[14px] h-[14px]">
              <rect x="2" y="1" width="8" height="11" rx="1.5" stroke="white" strokeWidth="1.2"/>
              <path d="M4 5h5M4 7.5h3.5M4 10h2" stroke="white" strokeWidth="1" strokeLinecap="round"/>
              <path d="M8 1v3h3" stroke="white" strokeWidth="1" strokeLinecap="round" strokeLinejoin="round"/>
            </svg>
          </div>
          <span className="font-serif text-[20px] tracking-[-0.2px] text-text-1">Nikhar</span>
        </div>

        <div className="bg-white border border-border-1 rounded-DEFAULT p-6 shadow-sm">
          <h1 className="font-serif text-[18px] text-text-1 mb-[2px]">Welcome back</h1>
          <p className="text-[12px] text-text-3 mb-5">Sign in to your workspace</p>

          <form onSubmit={handleSubmit}>
            <label className="block text-[10px] font-bold tracking-[0.5px] uppercase text-text-3 mb-1">Email</label>
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="w-full px-[10px] py-[8px] border border-border-1 rounded-sm bg-surface-2 text-text-1 font-sans text-[12.5px] outline-none focus:border-border-2 focus:bg-white transition-all mb-[11px]"
              placeholder="you@example.com"
              autoComplete="email"
            />

            <label className="block text-[10px] font-bold tracking-[0.5px] uppercase text-text-3 mb-1">Password</label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="w-full px-[10px] py-[8px] border border-border-1 rounded-sm bg-surface-2 text-text-1 font-sans text-[12.5px] outline-none focus:border-border-2 focus:bg-white transition-all mb-[11px]"
              placeholder="••••••••"
              autoComplete="current-password"
            />

            {error && (
              <div className="text-[11.5px] text-red bg-red-bg border border-red/20 rounded-sm px-3 py-2 mb-3">
                {error}
              </div>
            )}

            <button
              type="submit"
              disabled={mutation.isPending}
              className="w-full py-[10px] text-[13px] font-semibold rounded-DEFAULT bg-ink text-white border border-ink hover:bg-[#2e2b27] transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {mutation.isPending ? 'Signing in…' : 'Sign in'}
            </button>
          </form>
        </div>

        <p className="text-[11.5px] text-text-3 text-center mt-4">
          Don't have an account?{' '}
          <Link to="/register" className="text-ink font-semibold hover:underline">
            Start free trial
          </Link>
        </p>
      </div>
    </div>
  )
}
