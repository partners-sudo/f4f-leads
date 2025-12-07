import { useState, useEffect, useMemo } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { useInteractionReview, useAISuggestions, useApplyReview, useTemplates } from '@/hooks/useInteractionReviews'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { n8nApi } from '@/lib/n8n'
import { replaceTemplateVariables } from '@/lib/templateUtils'
import { supabase, type Template } from '@/lib/supabase'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'

export default function ReviewDetail() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const { data: review, isLoading } = useInteractionReview(id || '')
  const { mutate: getSuggestions, data: suggestions, isPending: loadingSuggestions } = useAISuggestions()
  const { mutate: applyReview, isPending: applying } = useApplyReview()

  const [selectedSuggestion, setSelectedSuggestion] = useState<number | null>(null)
  const [editedSubject, setEditedSubject] = useState('')
  const [editedBody, setEditedBody] = useState('')
  const [outcome, setOutcome] = useState<'f4f' | 'figgyz' | 'not_interested' | 'converted'>('f4f')
  const [assignedTo, setAssignedTo] = useState('')
  const [selectedTemplateId, setSelectedTemplateId] = useState<string>('')

  // Get brand from outcome for template filtering
  const brandForTemplates = useMemo(() => {
    if (outcome === 'f4f') return 'F4F'
    if (outcome === 'figgyz') return 'FiGGYZ'
    return undefined // Show all templates for other outcomes
  }, [outcome])

  const { data: templates, isLoading: templatesLoading, error: templatesError } = useTemplates(brandForTemplates)

  // Debug: Log template loading status
  useEffect(() => {
    console.log('Templates status:', { 
      loading: templatesLoading, 
      count: templates?.length || 0, 
      brand: brandForTemplates,
      error: templatesError 
    })
  }, [templates, templatesLoading, brandForTemplates, templatesError])

  // Clear selected template if it doesn't match the current brand filter
  useEffect(() => {
    if (selectedTemplateId && templates) {
      const selectedTemplate = templates.find((t) => t.id === selectedTemplateId)
      if (!selectedTemplate) {
        setSelectedTemplateId('')
      }
    }
  }, [templates, selectedTemplateId])

  const syncToErpMutation = useMutation({
    mutationFn: async (companyId: string) => {
      return n8nApi.syncToErp({ company_id: companyId })
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['erp-sync-logs'] })
      queryClient.invalidateQueries({ queryKey: ['interaction-review', id] })
    },
  })

  useEffect(() => {
    if (review && !suggestions) {
      // Auto-fetch suggestions when review loads
      const outreachLog = review.outreach_logs
      if (outreachLog && outreachLog.message_snippet) {
        getSuggestions({
          reply_text: outreachLog.message_snippet,
          contact_id: outreachLog.contact_id,
          company_id: outreachLog.company_id,
        })
      }
    }
  }, [review, suggestions, getSuggestions])

  const handleSelectSuggestion = (index: number) => {
    setSelectedSuggestion(index)
    setSelectedTemplateId('') // Clear template selection when using AI suggestion
    if (suggestions) {
      setEditedSubject(suggestions.suggestions[index].subject)
      setEditedBody(suggestions.suggestions[index].body)
      setOutcome(suggestions.suggestions[index].outcome)
    }
  }

  const handleSelectTemplate = (templateId: string) => {
    if (!templateId) {
      setSelectedTemplateId('')
      return
    }

    console.log('handleSelectTemplate called:', {
      templateId,
      templatesCount: templates?.length || 0,
      templates: templates?.map(t => ({ id: t.id, name: t.name, brand: t.brand })),
      brandForTemplates
    })

    setSelectedTemplateId(templateId)
    setSelectedSuggestion(null) // Clear suggestion selection when using template
    
    // Try to find template with both string and number comparison
    let template = templates?.find((t) => String(t.id) === String(templateId) || t.id === templateId)
    
    // If template not found in filtered list, try fetching it directly
    if (!template && templateId) {
      console.warn('Template not found in filtered list, fetching directly...', templateId)
      // Fetch the template directly from database
      supabase
        .from('templates')
        .select('*')
        .eq('id', templateId)
        .single()
        .then(({ data, error }: { data: Template | null; error: any }) => {
          if (error) {
            console.error('Error fetching template:', error)
            return
          }
          if (data) {
            // Apply the template
            if (!review) {
              setEditedSubject(data.subject)
              setEditedBody(data.body)
              return
            }
            const outreachLog = review.outreach_logs
            if (!outreachLog) {
              setEditedSubject(data.subject)
              setEditedBody(data.body)
              return
            }
            const variables = {
              name: outreachLog.contacts?.name || '',
              company: outreachLog.companies?.name || '',
              email: outreachLog.contacts?.email || '',
            }
            const subject = replaceTemplateVariables(data.subject, variables)
            const body = replaceTemplateVariables(data.body, variables)
            setEditedSubject(subject)
            setEditedBody(body)
            if (data.brand === 'F4F') {
              setOutcome('f4f')
            } else if (data.brand === 'FiGGYZ') {
              setOutcome('figgyz')
            }
          }
        })
      // Still return early since we're fetching asynchronously
      return
    }
    
    if (!template) {
      console.error('Template not found:', {
        templateId,
        availableTemplateIds: templates?.map(t => t.id) || [],
        templatesCount: templates?.length || 0
      })
      return
    }

    // If review is not loaded yet, just set the template ID and return
    // The template will be applied when review loads
    if (!review) {
      console.warn('Review not loaded yet, template selection will be applied when review loads')
      return
    }

    const outreachLog = review.outreach_logs
    if (!outreachLog) {
      console.warn('Outreach log not available')
      // Still set the template, but without variable replacement
      setEditedSubject(template.subject)
      setEditedBody(template.body)
      return
    }

    // Prepare variables for replacement
    const variables = {
      name: outreachLog.contacts?.name || '',
      company: outreachLog.companies?.name || '',
      email: outreachLog.contacts?.email || '',
    }

    // Replace variables in subject and body
    const subject = replaceTemplateVariables(template.subject, variables)
    const body = replaceTemplateVariables(template.body, variables)

    setEditedSubject(subject)
    setEditedBody(body)
    
    // Set outcome based on template brand
    if (template.brand === 'F4F') {
      setOutcome('f4f')
    } else if (template.brand === 'FiGGYZ') {
      setOutcome('figgyz')
    }
  }

  // Apply template when review/templates load if a template was already selected
  useEffect(() => {
    if (selectedTemplateId && review && templates && templates.length > 0) {
      const template = templates.find((t) => String(t.id) === String(selectedTemplateId) || t.id === selectedTemplateId)
      if (!template) {
        console.warn('Template not found in current templates list, trying to fetch all templates...')
        // Template might be filtered out - try fetching without brand filter
        return
      }

      const outreachLog = review.outreach_logs
      if (!outreachLog) {
        setEditedSubject(template.subject)
        setEditedBody(template.body)
        return
      }

      // Prepare variables for replacement
      const variables = {
        name: outreachLog.contacts?.name || '',
        company: outreachLog.companies?.name || '',
        email: outreachLog.contacts?.email || '',
      }

      // Replace variables in subject and body
      const subject = replaceTemplateVariables(template.subject, variables)
      const body = replaceTemplateVariables(template.body, variables)

      setEditedSubject(subject)
      setEditedBody(body)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [review, selectedTemplateId, templates])

  const handleSend = () => {
    if (!review || !editedSubject || !editedBody) return

    const outreachLog = review.outreach_logs
    if (!outreachLog) return

    applyReview(
      {
        interaction_review_id: review.id,
        chosen_subject: editedSubject,
        chosen_body: editedBody,
        outcome,
        assigned_to: assignedTo || 'Unassigned',
        contact_email: outreachLog.contacts?.email || '',
      },
      {
        onSuccess: () => {
          navigate('/reviews')
        },
      }
    )
  }

  if (isLoading) {
    return <div className="p-6">Loading...</div>
  }

  if (!review) {
    return <div className="p-6">Review not found</div>
  }

  const outreachLog = review.outreach_logs

  return (
    <div className="p-6 space-y-6">
      <div>
        <h1 className="text-3xl font-bold">Review Interaction</h1>
        <p className="text-muted-foreground">
          {outreachLog?.contacts?.name} - {outreachLog?.companies?.name}
        </p>
      </div>

      <Tabs defaultValue="inbound" className="space-y-4">
        <TabsList>
          <TabsTrigger value="inbound">Inbound Email</TabsTrigger>
          <TabsTrigger value="suggestions">AI Suggestions</TabsTrigger>
          <TabsTrigger value="send">Send Reply</TabsTrigger>
        </TabsList>

        <TabsContent value="inbound" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Inbound Email</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-2">
                <div>
                  <p className="text-sm text-muted-foreground">From</p>
                  <p className="font-medium">
                    {outreachLog?.contacts?.email || '-'}
                  </p>
                </div>
                <div>
                  <p className="text-sm text-muted-foreground">Message</p>
                  <div className="mt-2 p-4 bg-muted rounded-lg">
                    { review.notes || 'No message available'}
                  </div>
                </div>
                <div>
                  <p className="text-sm text-muted-foreground">Received</p>
                  <p className="font-medium">
                    {new Date(review.created_at).toLocaleString()}
                  </p>
                </div>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="suggestions" className="space-y-4">
          {loadingSuggestions ? (
            <div>Loading AI suggestions...</div>
          ) : suggestions ? (
            <div className="space-y-4">
              {suggestions.suggestions.map((suggestion, index) => (
                <Card
                  key={index}
                  className={`cursor-pointer ${
                    selectedSuggestion === index
                      ? 'border-primary border-2'
                      : ''
                  }`}
                  onClick={() => handleSelectSuggestion(index)}
                >
                  <CardHeader>
                    <CardTitle className="text-lg">
                      Suggestion {index + 1} - {suggestion.outcome.toUpperCase()}
                    </CardTitle>
                  </CardHeader>
                  <CardContent className="space-y-2">
                    <div>
                      <p className="text-sm text-muted-foreground">Subject</p>
                      <p className="font-medium">{suggestion.subject}</p>
                    </div>
                    <div>
                      <p className="text-sm text-muted-foreground">Body</p>
                      <div className="mt-2 p-4 bg-muted rounded-lg whitespace-pre-wrap">
                        {suggestion.body}
                      </div>
                    </div>
                    <Button
                      variant="outline"
                      onClick={() => handleSelectSuggestion(index)}
                    >
                      {selectedSuggestion === index ? 'Selected' : 'Select'}
                    </Button>
                  </CardContent>
                </Card>
              ))}
            </div>
          ) : (
            <div>
              <p className='pb-6'>No suggestions available. Click to generate:</p>
              <Button
                onClick={() => {
                  if (outreachLog && outreachLog.message_snippet) {
                    getSuggestions({
                      reply_text: review.notes || '',
                      contact_id: outreachLog.contact_id,
                      company_id: outreachLog.company_id,
                    })
                  }
                }}
                className='bg-emerald-500/20 hover:bg-emerald-500/40'
              >
                Generate Suggestions
              </Button>
            </div>
          )}
        </TabsContent>

        <TabsContent value="send" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Send Reply</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="template">Template (Optional)</Label>
                <select
                  id="template"
                  className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm disabled:opacity-50 disabled:cursor-not-allowed"
                  value={selectedTemplateId}
                  onChange={(e) => {
                    console.log('Template selected:', e.target.value)
                    handleSelectTemplate(e.target.value)
                  }}
                >
                  <option value="">Select a template...</option>
                  {templates?.map((template) => {
                    const templateId = String(template.id)
                    return (
                      <option key={templateId} value={templateId}>
                        {template.name} ({template.brand})
                      </option>
                    )
                  })}
                </select>
                {templates && templates.length === 0 && (
                  <p className="text-sm text-muted-foreground">
                    No templates available for {brandForTemplates || 'this outcome'}. 
                    <a href="/templates" className="text-primary underline ml-1">
                      Create one
                    </a>
                  </p>
                )}
                {templatesLoading && (
                  <p className="text-sm text-muted-foreground">
                    Loading templates...
                  </p>
                )}
                {templatesError && (
                  <p className="text-sm text-destructive">
                    Error loading templates: {templatesError instanceof Error ? templatesError.message : 'Unknown error'}
                  </p>
                )}
                {templates && templates.length > 0 && (
                  <p className="text-sm text-muted-foreground">
                    {templates.length} template(s) available
                  </p>
                )}
              </div>
              <div className="space-y-2">
                <Label htmlFor="subject">Subject</Label>
                <Input
                  id="subject"
                  value={editedSubject}
                  onChange={(e) => setEditedSubject(e.target.value)}
                  placeholder="Email subject"
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="body">Body</Label>
                <textarea
                  id="body"
                  className="flex min-h-[200px] w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
                  value={editedBody}
                  onChange={(e) => setEditedBody(e.target.value)}
                  placeholder="Email body"
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="outcome">Outcome</Label>
                <select
                  id="outcome"
                  className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
                  value={outcome}
                  onChange={(e) =>
                    setOutcome(
                      e.target.value as
                        | 'f4f'
                        | 'figgyz'
                        | 'not_interested'
                        | 'converted'
                    )
                  }
                >
                  <option value="f4f">F4F</option>
                  <option value="figgyz">FiGGYZ</option>
                  <option value="not_interested">Not Interested</option>
                  <option value="converted">Converted</option>
                </select>
              </div>
              <div className="space-y-2">
                <Label htmlFor="assigned">Assigned To</Label>
                <Input
                  id="assigned"
                  value={assignedTo}
                  onChange={(e) => setAssignedTo(e.target.value)}
                  placeholder="Name"
                />
              </div>
              <div className="flex gap-2">
                <Button onClick={handleSend} disabled={applying || !editedSubject || !editedBody}>
                  {applying ? 'Sending...' : 'Send Email'}
                </Button>
                <Button variant="outline" onClick={() => navigate('/reviews')}>
                  Cancel
                </Button>
              </div>
              {(outcome === 'converted' || review.outcome === 'converted') && outreachLog && (
                <div className="mt-4 pt-4 border-t">
                  <Button
                    onClick={() => {
                      if (confirm('Sync this company to ERP?')) {
                        syncToErpMutation.mutate(outreachLog.company_id)
                      }
                    }}
                    disabled={syncToErpMutation.isPending}
                    className="w-full"
                  >
                    {syncToErpMutation.isPending ? 'Syncing...' : 'Sync to ERP'}
                  </Button>
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  )
}

