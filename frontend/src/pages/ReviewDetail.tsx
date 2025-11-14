import { useState, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { useInteractionReview, useAISuggestions, useApplyReview } from '@/hooks/useInteractionReviews'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { n8nApi } from '@/lib/n8n'
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
    if (suggestions) {
      setEditedSubject(suggestions.suggestions[index].subject)
      setEditedBody(suggestions.suggestions[index].body)
      setOutcome(suggestions.suggestions[index].outcome)
    }
  }

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
                    {outreachLog?.message_snippet || review.notes || 'No message available'}
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
              <p>No suggestions available. Click to generate:</p>
              <Button
                onClick={() => {
                  if (outreachLog && outreachLog.message_snippet) {
                    getSuggestions({
                      reply_text: outreachLog.message_snippet,
                      contact_id: outreachLog.contact_id,
                      company_id: outreachLog.company_id,
                    })
                  }
                }}
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

