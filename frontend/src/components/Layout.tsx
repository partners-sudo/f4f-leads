import { Link, useLocation, useNavigate } from 'react-router-dom'
import { useAuth } from '@/hooks/useAuth'
import { Button } from '@/components/ui/button'
import {
  LayoutDashboard,
  Building2,
  Users,
  Mail,
  MessageSquare,
  FileText,
  GitMerge,
  Settings,
  LogOut,
} from 'lucide-react'

const navigation = [
  { name: 'Dashboard', href: '/dashboard', icon: LayoutDashboard },
  { name: 'Companies', href: '/companies', icon: Building2 },
  { name: 'Contacts', href: '/contacts', icon: Users },
  { name: 'Outreach Logs', href: '/outreach', icon: Mail },
  { name: 'Reviews', href: '/reviews', icon: MessageSquare },
  { name: 'Templates', href: '/templates', icon: FileText },
  { name: 'Merge Candidates', href: '/merge', icon: GitMerge },
  { name: 'ERP Sync', href: '/erp-sync', icon: Settings },
  { name: 'Scraping', href: '/scraping', icon: FileText },
]

export default function Layout({ children }: { children: React.ReactNode }) {
  const location = useLocation()
  const { signOut } = useAuth()
  const navigate = useNavigate()

  const handleSignOut = async () => {
    await signOut()
    navigate('/login')
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-950 via-slate-900 to-slate-950 text-slate-100">
      <div className="flex min-h-screen max-w-7xl mx-auto px-4 lg:px-6">
        {/* Sidebar */}
        <div className="relative hidden md:flex w-64 flex-col py-6 pr-4">
          <div className="relative flex-1 rounded-2xl border border-white/10 bg-slate-900/70 shadow-[0_20px_60px_rgba(15,23,42,0.9)] backdrop-blur-2xl overflow-hidden">
            <div className="pointer-events-none absolute inset-px rounded-[1.05rem] border border-white/10/60" />
            <div className="flex h-full flex-col">
              <div className="px-5 pt-4 pb-5 border-b border-white/5">
                <div className="flex items-center justify-between gap-2">
                  <div>
                    <h1 className="text-sm font-semibold tracking-tight">
                      F4F + FiGGYZ CRM
                    </h1>
                    <p className="mt-1 text-[0.7rem] uppercase tracking-[0.16em] text-slate-400">
                      Lead & outreach console
                    </p>
                  </div>
                  <span className="inline-flex h-7 items-center gap-1 rounded-full border border-emerald-400/30 bg-emerald-500/10 px-2 text-[0.65rem] font-medium text-emerald-200">
                    <span className="h-1.5 w-1.5 rounded-full bg-emerald-400 animate-pulse" />
                    Live
                  </span>
                </div>
              </div>

              <nav className="flex-1 space-y-1 px-2 py-3 overflow-y-auto">
                {navigation.map((item) => {
                  const Icon = item.icon
                  const isActive = location.pathname === item.href
                  return (
                    <Link
                      key={item.name}
                      to={item.href}
                      className={`group flex items-center gap-3 rounded-xl px-3 py-2 text-xs font-medium transition-all duration-150 ${
                        isActive
                          ? 'bg-slate-800/80 text-emerald-200 shadow-[0_10px_30px_rgba(15,23,42,0.8)]'
                          : 'text-slate-400 hover:text-slate-100 hover:bg-slate-800/60'
                      }`}
                    >
                      <span
                        className={`flex h-7 w-7 items-center justify-center rounded-lg border text-[0.8rem] transition-colors ${
                          isActive
                            ? 'border-emerald-400/60 bg-emerald-500/10 text-emerald-200'
                            : 'border-slate-700/70 bg-slate-900/60 text-slate-400 group-hover:border-emerald-400/50 group-hover:text-emerald-200'
                        }`}
                      >
                        <Icon className="h-4 w-4" />
                      </span>
                      <span className="truncate">{item.name}</span>
                    </Link>
                  )
                })}
              </nav>

              <div className="mt-auto border-t border-white/5 px-4 py-4">
                <Button
                  variant="ghost"
                  className="w-full justify-start gap-2 rounded-xl border border-transparent bg-slate-900/60 text-xs text-slate-300 transition-colors hover:border-red-400/40 hover:bg-red-500/10 hover:text-red-100"
                  onClick={handleSignOut}
                >
                  <LogOut className="h-4 w-4" />
                  Sign Out
                </Button>
              </div>
            </div>
          </div>
        </div>

        {/* Main content */}
        <div className="flex-1 py-6 md:pl-2">
          <main className="min-h-[calc(100vh-3rem)] rounded-2xl border border-white/10 bg-slate-900/60 shadow-[0_18px_50px_rgba(15,23,42,0.85)] backdrop-blur-2xl px-4 sm:px-6 lg:px-8 pb-10 pt-6 overflow-hidden">
            <div className="h-full overflow-y-auto custom-scrollbar">
              {children}
            </div>
          </main>
        </div>
      </div>
    </div>
  )
}
