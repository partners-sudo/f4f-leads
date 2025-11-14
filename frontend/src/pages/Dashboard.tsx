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
    <div className="p-6 space-y-6">
      <div>
        <h1 className="text-3xl font-bold">Dashboard</h1>
        <p className="text-muted-foreground">Overview of your CRM activity</p>
      </div>

      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        {cards.map((card) => {
          const Icon = card.icon
          return (
            <Card key={card.title}>
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium">
                  {card.title}
                </CardTitle>
                <Icon className="h-4 w-4 text-muted-foreground" />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">{card.value}</div>
                <p className="text-xs text-muted-foreground">
                  {card.description}
                </p>
              </CardContent>
            </Card>
          )
        })}
      </div>

      {stats.lastSyncAt && (
        <Card>
          <CardHeader>
            <CardTitle>Last ERP Sync</CardTitle>
            <CardDescription>
              {new Date(stats.lastSyncAt).toLocaleString()}
            </CardDescription>
          </CardHeader>
        </Card>
      )}
    </div>
  )
}

