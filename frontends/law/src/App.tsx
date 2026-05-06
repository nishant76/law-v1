import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { QueryClientProvider } from '@tanstack/react-query'
import { ReactQueryDevtools } from '@tanstack/react-query-devtools'
import { queryClient } from '@/lib/queryClient'
import AppShell from '@/components/layout/AppShell'
import ProtectedRoute from '@/components/auth/ProtectedRoute'

import HomePage from '@/pages/Home'
import DraftPage from '@/pages/Draft'
import PdfExtractorPage from '@/pages/PdfExtractor'
import DeadlinesPage from '@/pages/Deadlines'
import SearchPage from '@/pages/Search'
import SynopsisPage from '@/pages/Synopsis'
import ReplyPage from '@/pages/Reply'
import LegalProcessPage from '@/pages/LegalProcess'
import CasesPage from '@/pages/Cases'
import CaseDetailPage from '@/pages/Cases/CaseDetail'
import LoginPage from '@/pages/Login'
import RegisterPage from '@/pages/Register'

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <Routes>
          <Route path="/login" element={<LoginPage />} />
          <Route path="/register" element={<RegisterPage />} />
          <Route
            element={
              <ProtectedRoute>
                <AppShell />
              </ProtectedRoute>
            }
          >
            <Route path="/" element={<HomePage />} />
            <Route path="/draft" element={<DraftPage />} />
            <Route path="/pdf" element={<PdfExtractorPage />} />
            <Route path="/deadlines" element={<DeadlinesPage />} />
            <Route path="/search" element={<SearchPage />} />
            <Route path="/synopsis" element={<SynopsisPage />} />
            <Route path="/reply" element={<ReplyPage />} />
            <Route path="/legal-process" element={<LegalProcessPage />} />
            <Route path="/cases" element={<CasesPage />} />
            <Route path="/cases/:id" element={<CaseDetailPage />} />
          </Route>
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </BrowserRouter>
      <ReactQueryDevtools initialIsOpen={false} />
    </QueryClientProvider>
  )
}
