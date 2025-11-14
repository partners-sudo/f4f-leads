import { useQuery } from '@tanstack/react-query'
import { supabase } from '@/lib/supabase'

export function useDashboardStats() {
  return useQuery({
    queryKey: ['dashboard-stats'],
    queryFn: async () => {
      const today = new Date().toISOString().split('T')[0]

      // Total companies
      const { count: totalCompanies } = await supabase
        .from('companies')
        .select('*', { count: 'exact', head: true })

      // Total contacts
      const { count: totalContacts } = await supabase
        .from('contacts')
        .select('*', { count: 'exact', head: true })

      // Validated contacts (confidence_score > 0.7)
      const { count: validatedContacts } = await supabase
        .from('contacts')
        .select('*', { count: 'exact', head: true })
        .gt('confidence_score', 0.7)

      // Outreach emails sent today
      const { count: emailsSentToday } = await supabase
        .from('outreach_logs')
        .select('*', { count: 'exact', head: true })
        .gte('sent_at', today)

      // Opened today
      const { count: openedToday } = await supabase
        .from('outreach_logs')
        .select('*', { count: 'exact', head: true })
        .gte('opened_at', today)

      // Replies today
      const { count: repliesToday } = await supabase
        .from('outreach_logs')
        .select('*', { count: 'exact', head: true })
        .gte('replied_at', today)
        .eq('status', 'replied')

      // Pending interactions
      const { count: pendingInteractions } = await supabase
        .from('interaction_reviews')
        .select('*', { count: 'exact', head: true })
        .eq('outcome', 'pending')

      // Cold contacts (completed sequences, no response)
      const { count: coldContacts } = await supabase
        .from('outreach_logs')
        .select('*', { count: 'exact', head: true })
        .eq('sequence_stage', 2)
        .is('replied_at', null)

      // Last sync to ERP
      const { data: lastSync } = await supabase
        .from('crm_to_erp_log')
        .select('synced_at')
        .order('synced_at', { ascending: false })
        .limit(1)
        .single()

      return {
        totalCompanies: totalCompanies || 0,
        totalContacts: totalContacts || 0,
        validatedContacts: validatedContacts || 0,
        emailsSentToday: emailsSentToday || 0,
        openedToday: openedToday || 0,
        repliesToday: repliesToday || 0,
        pendingInteractions: pendingInteractions || 0,
        coldContacts: coldContacts || 0,
        lastSyncAt: lastSync?.synced_at || null,
      }
    },
    refetchInterval: 30000, // Refetch every 30 seconds
  })
}

