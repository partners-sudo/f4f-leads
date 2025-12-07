import { useDashboardStats } from '@/hooks/useDashboard'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Building2, Users, Mail, MessageSquare, Clock, TrendingDown } from 'lucide-react'

export default function Dashboard() {
  const { data: stats, isLoading } = useDashboardStats()

  if (isLoading) {
    return <div className="p-6">Loading dashboard...</div>
  }

  if (!stats) {
    return <div className="p-6">Failed to load dashboard</div>
  }

  const cards = [
    {
      title: 'Total Companies',
      value: stats.totalCompanies,
      description: 'All companies in database',
      icon: Building2,
    },
    {
      title: 'Total Contacts',
      value: stats.totalContacts,
      description: 'All contacts',
      icon: Users,
    },
    {
      title: 'Validated Contacts',
      value: stats.validatedContacts,
      description: 'Confidence score > 0.7',
      icon: Users,
    },
    {
      title: 'Emails Sent Today',
      value: stats.emailsSentToday,
      description: 'Outreach emails sent',
      icon: Mail,
    },
    {
      title: 'Opened Today',
      value: stats.openedToday,
      description: 'Emails opened',
      icon: Mail,
    },
    {
      title: 'Replies Today',
      value: stats.repliesToday,
      description: 'Replies received',
      icon: MessageSquare,
    },
    {
      title: 'Pending Reviews',
      value: stats.pendingInteractions,
      description: 'Awaiting review',
      icon: Clock,
    },
    {
      title: 'Cold Contacts',
      value: stats.coldContacts,
      description: 'No response after sequence',
      icon: TrendingDown,
    },
  ]

  return (
    <div className="space-y-8">
      <div className="flex flex-col gap-2">
        <h1 className="text-2xl md:text-3xl font-semibold tracking-tight text-slate-50">
          Overview
        </h1>
        <p className="text-sm text-slate-400">
          High-level stats across companies, contacts, outreach, and reviews.
        </p>
      </div>

      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        {cards.map((card) => {
          const Icon = card.icon
          return (
            <Card
              key={card.title}
              className="relative overflow-hidden border-white/10 bg-slate-900/70 text-slate-100 shadow-[0_16px_40px_rgba(15,23,42,0.9)] transition-transform duration-200 ease-out hover:-translate-y-[2px]"
            >
              <div className="pointer-events-none absolute inset-0 bg-gradient-to-br from-emerald-400/5 via-sky-400/0 to-indigo-500/10" />
              <CardHeader className="relative flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-xs font-medium uppercase tracking-[0.18em] text-slate-400">
                  {card.title}
                </CardTitle>
                <span className="inline-flex h-8 w-8 items-center justify-center rounded-lg border border-white/10 bg-slate-900/70 text-emerald-200">
                  <Icon className="h-4 w-4" />
                </span>
              </CardHeader>
              <CardContent className="relative space-y-1">
                <div className="text-2xl font-semibold tracking-tight">{card.value}</div>
                <p className="text-[0.7rem] text-slate-400">
                  {card.description}
                </p>
              </CardContent>
            </Card>
          )
        })}
      </div>

      {stats.lastSyncAt && (
        <Card className="mt-2 border-white/10 bg-slate-900/70 text-slate-100">
          <CardHeader className="flex flex-row items-center justify-between gap-4">
            <div>
              <CardTitle className="text-sm font-medium tracking-tight">
                Last ERP Sync
              </CardTitle>
              <CardDescription className="text-xs text-slate-400">
                {new Date(stats.lastSyncAt).toLocaleString()}
              </CardDescription>
            </div>
            <span className="inline-flex items-center gap-2 rounded-full border border-emerald-400/40 bg-emerald-500/10 px-3 py-1 text-[0.7rem] font-medium text-emerald-200">
              <span className="h-1.5 w-1.5 rounded-full bg-emerald-400 animate-pulse" />
              ERP / Retool
            </span>
          </CardHeader>
        </Card>
      )}
    </div>
  )
}

