import { useState } from 'react'
import { Outlet } from 'react-router-dom'
import Sidebar from './Sidebar'
import Topbar from './Topbar'
import BottomNav from './BottomNav'
import ToastContainer from '@/components/ui/ToastContainer'
import { useAuthStore } from '@/store/authStore'

export default function AppShell() {
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const user = useAuthStore((s) => s.user)
  const firstName = user?.full_name?.split(' ')[0]

  return (
    <div className="flex h-full overflow-hidden">
      <Sidebar open={sidebarOpen} onClose={() => setSidebarOpen(false)} />

      <main className="flex-1 min-w-0 flex flex-col overflow-hidden">
        <Topbar onHamburger={() => setSidebarOpen(true)} userName={firstName} />
        <div className="flex-1 overflow-y-auto p-[22px] md:p-[22px] pb-4">
          <Outlet />
        </div>
        <BottomNav />
      </main>

      <ToastContainer />
    </div>
  )
}
