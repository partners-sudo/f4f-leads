// n8n API client
const N8N_BASE_URL = import.meta.env.VITE_N8N_BASE_URL || ''

export interface AISuggestReplyRequest {
  reply_text: string
  contact_id: number | string
  company_id: number | string
}

export interface AISuggestReplyResponse {
  suggestions: Array<{
    subject: string
    body: string
    outcome: 'f4f' | 'figgyz' | 'not_interested'
  }>
}

// Raw response from n8n
interface N8nChoicesResponse {
  choices: Array<{
    type: string
    subject: string
    body: string
  }>
}

export interface ApplyReviewRequest {
  interaction_review_id: number | string
  chosen_subject: string
  chosen_body: string
  outcome: 'f4f' | 'figgyz' | 'not_interested' | 'converted'
  assigned_to: string
  contact_email: string
}

export interface SyncToErpRequest {
  company_id: number | string
}

export const n8nApi = {
  async suggestReplies(data: AISuggestReplyRequest): Promise<AISuggestReplyResponse> {
    const response = await fetch(`${N8N_BASE_URL}/ai-suggest-replies`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(data),
    })
    
    if (!response.ok) {
      throw new Error(`n8n API error: ${response.statusText}`)
    }
    
    const rawResponse: N8nChoicesResponse = await response.json()
    
    // Transform n8n response format to expected format
    const suggestions = rawResponse.choices.map((choice) => {
      // Map type to outcome (case-insensitive matching)
      const typeLower = choice.type.toLowerCase()
      let outcome: 'f4f' | 'figgyz' | 'not_interested' = 'f4f'
      
      if (typeLower.includes('figgyz')) {
        outcome = 'figgyz'
      } else if (typeLower.includes('decline') || typeLower.includes('not interested')) {
        outcome = 'not_interested'
      } else if (typeLower.includes('first 4 figures') || typeLower.includes('f4f')) {
        outcome = 'f4f'
      }
      
      return {
        subject: choice.subject,
        body: choice.body,
        outcome,
      }
    })
    
    return { suggestions }
  },

  async applyReview(data: ApplyReviewRequest): Promise<void> {
    const response = await fetch(`${N8N_BASE_URL}/apply-review`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(data),
    })
    
    if (!response.ok) {
      throw new Error(`n8n API error: ${response.statusText}`)
    }
  },

  async syncToErp(data: SyncToErpRequest): Promise<void> {
    const response = await fetch(`${N8N_BASE_URL}/sync-to-erp`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(data),
    })
    
    if (!response.ok) {
      throw new Error(`n8n API error: ${response.statusText}`)
    }
  },
}

