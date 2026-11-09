import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { BrowserRouter, Navigate, Route, Routes, useLocation } from 'react-router-dom'
import { useEffect } from 'react'
import { TopBar } from './components/TopBar'
import { AuthProvider, useAuth } from './lib/auth'
import { Landing } from './pages/Landing'
import { LeaderboardPage } from './pages/LeaderboardPage'
import { MapPage } from './pages/MapPage'
import { ModulePage } from './pages/ModulePage'
import { ProfilePage } from './pages/ProfilePage'

const queryClient = new QueryClient({
  defaultOptions: { queries: { staleTime: 15_000, refetchOnWindowFocus: false } },
})

function ScrollToTop() {
  const { pathname } = useLocation()
  useEffect(() => {
    window.scrollTo({ top: 0 })
  }, [pathname])
  return null
}

function Routed() {
  const { token } = useAuth()
  if (!token) return <Landing />
  return (
    <div className="shell">
      <TopBar />
      <ScrollToTop />
      <main className="container">
        <Routes>
          <Route path="/" element={<MapPage />} />
          <Route path="/learn/:slug" element={<ModulePage />} />
          <Route path="/learn/:slug/:activityId" element={<ModulePage />} />
          <Route path="/leaderboard" element={<LeaderboardPage />} />
          <Route path="/profile" element={<ProfilePage />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </main>
    </div>
  )
}

export function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <AuthProvider>
        <BrowserRouter>
          <Routed />
        </BrowserRouter>
      </AuthProvider>
    </QueryClientProvider>
  )
}
