import { createClient } from '@supabase/supabase-js'

// These should be set as environment variables
const supabaseUrl = import.meta.env.VITE_SUPABASE_URL || ''
const supabaseAnonKey = import.meta.env.VITE_SUPABASE_ANON_KEY || ''

export const supabase = createClient(supabaseUrl, supabaseAnonKey)

// Database types (to be updated based on actual schema)
export type Company = {
  id: string
  name: string
  domain: string | null
  country: string | null
  region: string | null
  type: string | null
  source: string | null
  brand_focus: string | null
  status: 'new' | 'active' | 'merged' | 'cold'
  created_at: string
  updated_at: string
}

export type Contact = {
  id: string
  company_id: string
  name: string
  email: string
  phone: string | null
  title: string | null
  linkedin_url: string | null
  confidence_score: number | null
  last_validated: string | null
  created_at: string
  updated_at: string
}

export type OutreachLog = {
  id: string
  company_id: string
  contact_id: string
  sequence_stage: number
  sent_at: string | null
  opened_at: string | null
  replied_at: string | null
  message_snippet: string | null
  provider_message_id: string | null
  status: 'sent' | 'bounced' | 'failed' | 'replied' | 'stopped'
  created_at: string
}

export type InteractionReview = {
  id: string
  outreach_log_id: string
  assigned_to: string | null
  notes: string | null
  outcome: 'pending' | 'f4f' | 'figgyz' | 'not_interested' | 'converted'
  created_at: string
}

export type Template = {
  id: string
  name: string
  brand: string
  subject: string
  body: string
  variables: string | null
  created_at: string
}

export type MergeCandidate = {
  id: string
  company_a: string
  company_b: string
  score: number
  payload: any
  created_at: string
}

export type CrmToErpLog = {
  id: string
  company_id: string
  synced_at: string
  payload: any
}

