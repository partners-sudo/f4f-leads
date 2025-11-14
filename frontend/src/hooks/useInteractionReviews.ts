import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { supabase, type InteractionReview, type Template } from '@/lib/supabase'
import { n8nApi } from '@/lib/n8n'

export function useInteractionReviews(filters?: {
  assigned_to?: string
  outcome?: string
  date?: string
}) {
  return useQuery({
    queryKey: ['interaction-reviews', filters],
    queryFn: async () => {
      let query = supabase
        .from('interaction_reviews')
        .select(`
          *,
          outreach_logs:outreach_log_id (
            *,
            contacts:contact_id (name, email),
            companies:company_id (name)
          )
        `)

      if (filters?.assigned_to) {
        query = query.eq('assigned_to', filters.assigned_to)
      }
      if (filters?.outcome) {
        query = query.eq('outcome', filters.outcome)
      }
      if (filters?.date) {
        query = query.gte('created_at', filters.date)
      }

      const { data, error } = await query.order('created_at', { ascending: false })

      if (error) throw error
      
      // Transform the data to match expected structure
      return (data || []).map((review: any) => ({
        ...review,
        outreach_logs: Array.isArray(review.outreach_logs) 
          ? review.outreach_logs[0] 
          : review.outreach_logs,
      })) as (InteractionReview & {
        outreach_logs: {
          contacts: { name: string; email: string }
          companies: { name: string }
        }
      })[]
    },
  })
}

export function useInteractionReview(id: string) {
  return useQuery({
    queryKey: ['interaction-review', id],
    queryFn: async () => {
      const { data, error } = await supabase
        .from('interaction_reviews')
        .select(`
          *,
          outreach_logs:outreach_log_id (
            *,
            contacts:contact_id (*),
            companies:company_id (*)
          )
        `)
        .eq('id', id)
        .single()

      if (error) throw error
      
      // Transform nested structure
      const transformed = {
        ...data,
        outreach_logs: Array.isArray(data.outreach_logs) 
          ? data.outreach_logs[0] 
          : data.outreach_logs,
      }
      
      return transformed
    },
    enabled: !!id,
  })
}

export function useAISuggestions() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async (data: { reply_text: string; contact_id: string; company_id: string }) => {
      return n8nApi.suggestReplies(data)
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['interaction-reviews'] })
    },
  })
}

export function useApplyReview() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async (data: {
      interaction_review_id: string
      chosen_subject: string
      chosen_body: string
      outcome: string
      assigned_to: string
      contact_email: string
    }) => {
      return n8nApi.applyReview(data)
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['interaction-reviews'] })
    },
  })
}

export function useTemplates(brand?: string) {
  return useQuery({
    queryKey: ['templates', brand],
    queryFn: async () => {
      let query = supabase
        .from('templates')
        .select('*')
        .order('created_at', { ascending: false })

      if (brand) {
        query = query.eq('brand', brand)
      }

      const { data, error } = await query

      if (error) throw error
      return data as Template[]
    },
  })
}

