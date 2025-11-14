import { useParams } from 'react-router-dom'
import { useContact } from '@/hooks/useContacts'
import { useOutreachLogs } from '@/hooks/useOutreachLogs'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'

export default function ContactDetail() {
  const { id } = useParams<{ id: string }>()
  const { data: contact, isLoading } = useContact(id || '')
  const { data: outreachLogs, isLoading: outreachLogsLoading, error: outreachLogsError } = useOutreachLogs()

  if (isLoading) {
    return <div className="p-6">Loading...</div>
  }

  if (!contact) {
    return <div className="p-6">Contact not found</div>
  }

  // Filter logs for this contact - handle both string and UUID comparison
  const contactOutreachLogs = outreachLogs?.filter((log) => {
    const logContactId = String(log.contact_id)
    const contactId = String(id)
    return logContactId === contactId
  }) || []

  // Debug logging
  if (outreachLogs && id) {
    console.log('Contact ID (from URL):', id, typeof id)
    console.log('Total outreach logs fetched:', outreachLogs.length)
    console.log('Contact outreach logs (filtered):', contactOutreachLogs.length)
    if (outreachLogs.length > 0) {
      console.log('First log contact_id:', outreachLogs[0]?.contact_id, typeof outreachLogs[0]?.contact_id)
      console.log('All unique contact_ids in logs:', [...new Set(outreachLogs.map(log => log.contact_id))])
      console.log('Does first log match?', String(outreachLogs[0]?.contact_id) === String(id))
    }
  }

  const logsByStage = {
    0: contactOutreachLogs.filter((log) => log.sequence_stage === 0),
    1: contactOutreachLogs.filter((log) => log.sequence_stage === 1),
    2: contactOutreachLogs.filter((log) => log.sequence_stage === 2),
  }

  return (
    <div className="p-6 space-y-6">
      <div>
        <h1 className="text-3xl font-bold">{contact.name}</h1>
        <p className="text-muted-foreground">{contact.email}</p>
      </div>

      <Tabs defaultValue="overview" className="space-y-4">
        <TabsList>
          <TabsTrigger value="overview">Overview</TabsTrigger>
          <TabsTrigger value="outreach">Outreach Sequence</TabsTrigger>
        </TabsList>

        <TabsContent value="overview" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Contact Information</CardTitle>
            </CardHeader>
            <CardContent className="space-y-2">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <p className="text-sm text-muted-foreground">Email</p>
                  <p className="font-medium">{contact.email}</p>
                </div>
                <div>
                  <p className="text-sm text-muted-foreground">Phone</p>
                  <p className="font-medium">{contact.phone || '-'}</p>
                </div>
                <div>
                  <p className="text-sm text-muted-foreground">Title</p>
                  <p className="font-medium">{contact.title || '-'}</p>
                </div>
                <div>
                  <p className="text-sm text-muted-foreground">Confidence Score</p>
                  <p className="font-medium">
                    {contact.confidence_score
                      ? (contact.confidence_score * 100).toFixed(0) + '%'
                      : '-'}
                  </p>
                </div>
                <div>
                  <p className="text-sm text-muted-foreground">LinkedIn</p>
                  <p className="font-medium">
                    {contact.linkedin_url ? (
                      <a
                        href={contact.linkedin_url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-primary hover:underline"
                      >
                        View Profile
                      </a>
                    ) : (
                      '-'
                    )}
                  </p>
                </div>
                <div>
                  <p className="text-sm text-muted-foreground">Last Validated</p>
                  <p className="font-medium">
                    {contact.last_validated
                      ? new Date(contact.last_validated).toLocaleString()
                      : '-'}
                  </p>
                </div>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="outreach" className="space-y-4">
          {outreachLogsError && (
            <div className="bg-red-50 border border-red-200 rounded-lg p-4">
              <p className="text-red-800 font-medium">Error loading outreach history</p>
              <p className="text-red-600 text-sm mt-1">
                {outreachLogsError instanceof Error ? outreachLogsError.message : 'Unknown error occurred'}
              </p>
            </div>
          )}
          {outreachLogsLoading ? (
            <div className="text-center py-8">Loading outreach history...</div>
          ) : contactOutreachLogs.length === 0 ? (
            <div className="text-center py-8 text-muted-foreground">
              <p className="text-lg font-medium mb-2">No outreach history</p>
              <p className="text-sm">No outreach emails have been sent to this contact yet.</p>
            </div>
          ) : (
            <div className="space-y-6">
              {[0, 1, 2].map((stage) => (
                <Card key={stage}>
                  <CardHeader>
                    <CardTitle>Stage {stage}</CardTitle>
                  </CardHeader>
                  <CardContent>
                    {logsByStage[stage as keyof typeof logsByStage].length > 0 ? (
                      <div className="border rounded-lg">
                        <Table>
                          <TableHeader>
                            <TableRow>
                              <TableHead>Sent At</TableHead>
                              <TableHead>Opened At</TableHead>
                              <TableHead>Replied At</TableHead>
                              <TableHead>Status</TableHead>
                              <TableHead>Message Snippet</TableHead>
                            </TableRow>
                          </TableHeader>
                          <TableBody>
                            {logsByStage[stage as keyof typeof logsByStage].map(
                              (log) => (
                                <TableRow key={log.id}>
                                  <TableCell>
                                    {log.sent_at
                                      ? new Date(log.sent_at).toLocaleString()
                                      : '-'}
                                  </TableCell>
                                  <TableCell>
                                    {log.opened_at
                                      ? new Date(log.opened_at).toLocaleString()
                                      : '-'}
                                  </TableCell>
                                  <TableCell>
                                    {log.replied_at
                                      ? new Date(log.replied_at).toLocaleString()
                                      : '-'}
                                  </TableCell>
                                  <TableCell>
                                    <span
                                      className={`px-2 py-1 rounded text-xs ${
                                        log.status === 'replied'
                                          ? 'bg-green-100 text-green-800'
                                          : log.status === 'sent'
                                          ? 'bg-blue-100 text-blue-800'
                                          : log.status === 'bounced' || log.status === 'failed'
                                          ? 'bg-red-100 text-red-800'
                                          : 'bg-gray-100 text-gray-800'
                                      }`}
                                    >
                                      {log.status}
                                    </span>
                                  </TableCell>
                                  <TableCell className="max-w-xs truncate">
                                    {log.message_snippet || '-'}
                                  </TableCell>
                                </TableRow>
                              )
                            )}
                          </TableBody>
                        </Table>
                      </div>
                    ) : (
                      <p className="text-muted-foreground">No logs for this stage</p>
                    )}
                  </CardContent>
                </Card>
              ))}
            </div>
          )}
        </TabsContent>
      </Tabs>
    </div>
  )
}

