import { useQuery } from '@tanstack/react-query'
import { supabase, type OutreachLog } from '@/lib/supabase'

export function useOutreachLogs(filters?: {
  stage?: string | number
  brand?: string
  status?: string
  dateFrom?: string
  dateTo?: string
}) {
  return useQuery({
    queryKey: ['outreach-logs', filters],
    queryFn: async () => {
      // Try with joins first
      let query = supabase
        .from('outreach_logs')
        .select(`
          *,
          contacts!contact_id (name, email),
          companies!company_id (name, brand_focus)
        `)

      if (filters?.stage !== undefined && filters.stage !== null) {
        const stageNum = parseInt(filters.stage.toString())
        if (!isNaN(stageNum)) {
          query = query.eq('sequence_stage', stageNum)
        }
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

      let { data, error } = await query.order('created_at', { ascending: false })

      // If join fails, try without joins and fetch separately
      if (error && (error.code === 'PGRST116' || error.message?.includes('foreign key'))) {
        console.warn('Join failed, fetching data separately:', error.message)
        
        // Fetch logs without joins
        let simpleQuery = supabase.from('outreach_logs').select('*')
        
        if (filters?.stage !== undefined && filters.stage !== null) {
          const stageNum = parseInt(filters.stage.toString())
          if (!isNaN(stageNum)) {
            simpleQuery = simpleQuery.eq('sequence_stage', stageNum)
          }
        }
        if (filters?.status) {
          simpleQuery = simpleQuery.eq('status', filters.status)
        }
        if (filters?.dateFrom) {
          simpleQuery = simpleQuery.gte('created_at', filters.dateFrom)
        }
        if (filters?.dateTo) {
          simpleQuery = simpleQuery.lte('created_at', filters.dateTo)
        }

        const { data: logsData, error: logsError } = await simpleQuery.order('created_at', { ascending: false })
        
        if (logsError) {
          console.error('Error fetching outreach logs:', logsError)
          throw logsError
        }

        // Fetch contacts and companies separately
        const contactIds = [...new Set((logsData || []).map((log: any) => log.contact_id))]
        const companyIds = [...new Set((logsData || []).map((log: any) => log.company_id))]

        const [contactsResult, companiesResult] = await Promise.all([
          contactIds.length > 0 
            ? supabase.from('contacts').select('id, name, email').in('id', contactIds)
            : Promise.resolve({ data: [], error: null }),
          companyIds.length > 0
            ? supabase.from('companies').select('id, name, brand_focus').in('id', companyIds)
            : Promise.resolve({ data: [], error: null }),
        ])

        const contactsMap = new Map((contactsResult.data || []).map((c: any) => [c.id, c]))
        const companiesMap = new Map((companiesResult.data || []).map((c: any) => [c.id, c]))

        // Combine data
        data = (logsData || []).map((log: any) => ({
          ...log,
          contacts: contactsMap.get(log.contact_id) || null,
          companies: companiesMap.get(log.company_id) || null,
        }))
      } else if (error) {
        console.error('Error fetching outreach logs:', error)
        throw error
      }
      
      // Filter by brand after fetching if needed
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
        contacts: { name: string; email: string } | null
        companies: { name: string; brand_focus: string } | null
      })[]
    },
  })
}
