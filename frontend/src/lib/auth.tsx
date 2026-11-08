import { createContext, useCallback, useContext, useEffect, useState, type ReactNode } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import { api, setUnauthorizedHandler, tokenStore } from '../api/client'

interface AuthState {
  token: string | null
  login: (username: string, password: string) => Promise<void>
  register: (username: string, displayName: string, password: string) => Promise<void>
  logout: () => void
}

const Ctx = createContext<AuthState | null>(null)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [token, setToken] = useState<string | null>(() => tokenStore.get())
  const qc = useQueryClient()

  const accept = useCallback((t: string | null) => {
    tokenStore.set(t)
    setToken(t)
    qc.clear()
  }, [qc])

  useEffect(() => setUnauthorizedHandler(() => accept(null)), [accept])

  const value: AuthState = {
    token,
    login: async (username, password) => {
      const r = await api<{ token: string }>('/auth/login', { body: { username, password } })
      accept(r.token)
    },
    register: async (username, display_name, password) => {
      const r = await api<{ token: string }>('/auth/register', { body: { username, display_name, password } })
      accept(r.token)
    },
    logout: () => accept(null),
  }
  return <Ctx.Provider value={value}>{children}</Ctx.Provider>
}

export function useAuth(): AuthState {
  const v = useContext(Ctx)
  if (!v) throw new Error('useAuth outside AuthProvider')
  return v
}
