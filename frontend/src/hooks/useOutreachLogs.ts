import { useQuery } from '@tanstack/react-query'
import { supabase, type OutreachLog } from '@/lib/supabase'

export function useOutreachLogs(filters?: {
  stage?: number
  brand?: string
  status?: string
  dateFrom?: string
  dateTo?: string
}) {
  return useQuery({
    queryKey: ['outreach-logs', filters],
    queryFn: async () => {
      let query = supabase
        .from('outreach_logs')
        .select(`
          *,
          contacts:contact_id (name, email),
          companies:company_id (name, brand_focus)
        `)

      if (filters?.stage !== undefined) {
        query = query.eq('sequence_stage', filters.stage)
      }
      if (filters?.status) {
        query = query.eq('status', filters.status)
      }
      if (filters?.dateFrom) {
        query = query.gte('created_at', filters.dateFrom)
      }
      if (filters?.dateTo) {
        query = query.lte('created_at', filters.dateTo)
      }

      const { data, error } = await query.order('created_at', { ascending: false })

      if (error) throw error
      
      // Filter by brand after fetching if needed (since we can't filter nested relations easily)
      let filteredData = data || []
      if (filters?.brand) {
        filteredData = filteredData.filter((log: any) => {
          const company = Array.isArray(log.companies) ? log.companies[0] : log.companies
          return company?.brand_focus === filters.brand
        })
      }
      
      // Transform nested arrays to single objects
      return filteredData.map((log: any) => ({
        ...log,
        contacts: Array.isArray(log.contacts) ? log.contacts[0] : log.contacts,
        companies: Array.isArray(log.companies) ? log.companies[0] : log.companies,
      })) as (OutreachLog & {
        contacts: { name: string; email: string }
        companies: { name: string; brand_focus: string }
      })[]
    },
  })
}
