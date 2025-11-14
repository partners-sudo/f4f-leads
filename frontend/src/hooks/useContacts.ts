import { useQuery } from '@tanstack/react-query'
import { supabase, type Contact } from '@/lib/supabase'

export function useContacts(companyId?: string) {
  return useQuery({
    queryKey: ['contacts', companyId],
    queryFn: async () => {
      let query = supabase
        .from('contacts')
        .select('*, companies:company_id (id, name)')

      if (companyId) {
        query = query.eq('company_id', companyId)
      }

      const { data, error } = await query.order('created_at', { ascending: false })

      if (error) throw error
      
      // Transform nested structure
      return (data || []).map((contact: any) => ({
        ...contact,
        company: Array.isArray(contact.companies) ? contact.companies[0] : contact.companies,
      })) as (Contact & { company?: { id: string; name: string } })[]
    },
  })
}

export function useContact(id: string) {
  return useQuery({
    queryKey: ['contact', id],
    queryFn: async () => {
      const { data, error } = await supabase
        .from('contacts')
        .select('*, companies(*)')
        .eq('id', id)
        .single()

      if (error) throw error
      return data as Contact & { companies: any }
    },
    enabled: !!id,
  })
}

