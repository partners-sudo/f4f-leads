import { useQuery } from '@tanstack/react-query'
import { supabase, type Company } from '@/lib/supabase'

export function useCompanies(filters?: {
  region?: string
  country?: string
  brand_focus?: string
  status?: string
  source?: string
}) {
  return useQuery({
    queryKey: ['companies', filters],
    queryFn: async () => {
      let query = supabase.from('companies').select('*')

      if (filters?.region) {
        query = query.eq('region', filters.region)
      }
      if (filters?.country) {
        query = query.eq('country', filters.country)
      }
      if (filters?.brand_focus) {
        query = query.eq('brand_focus', filters.brand_focus)
      }
      if (filters?.status) {
        query = query.eq('status', filters.status)
      }
      if (filters?.source) {
        query = query.eq('source', filters.source)
      }

      const { data, error } = await query.order('created_at', { ascending: false })

      if (error) {
        console.error('Error fetching companies:', error)
        throw error
      }
      
      console.log('Fetched companies:', data?.length || 0, 'companies')
      return (data || []) as Company[]
    },
  })
}

export function useCompany(id: string) {
  return useQuery({
    queryKey: ['company', id],
    queryFn: async () => {
      const { data, error } = await supabase
        .from('companies')
        .select('*')
        .eq('id', id)
        .single()

      if (error) throw error
      return data as Company
    },
    enabled: !!id,
  })
}

