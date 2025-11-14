import { useParams, Link } from 'react-router-dom'
import { useCompany } from '@/hooks/useCompanies'
import { useContacts } from '@/hooks/useContacts'
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

export default function CompanyDetail() {
  const { id } = useParams<{ id: string }>()
  const { data: company, isLoading: companyLoading } = useCompany(id || '')
  const { data: contacts, isLoading: contactsLoading } = useContacts(id)
  const { data: outreachLogs } = useOutreachLogs()

  if (companyLoading) {
    return <div className="p-6">Loading...</div>
  }

  if (!company) {
    return <div className="p-6">Company not found</div>
  }

  const companyOutreachLogs = outreachLogs?.filter(
    (log) => log.company_id === id
  ) || []

  return (
    <div className="p-6 space-y-6">
      <div>
        <h1 className="text-3xl font-bold">{company.name}</h1>
        <p className="text-muted-foreground">{company.domain}</p>
      </div>

      <Tabs defaultValue="overview" className="space-y-4">
        <TabsList>
          <TabsTrigger value="overview">Overview</TabsTrigger>
          <TabsTrigger value="contacts">Contacts</TabsTrigger>
          <TabsTrigger value="outreach">Outreach History</TabsTrigger>
        </TabsList>

        <TabsContent value="overview" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Company Information</CardTitle>
            </CardHeader>
            <CardContent className="space-y-2">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <p className="text-sm text-muted-foreground">Domain</p>
                  <p className="font-medium">
                    {company.domain ? (
                      <a
                        href={`https://${company.domain}`}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-primary hover:underline"
                      >
                        {company.domain}
                      </a>
                    ) : (
                      '-'
                    )}
                  </p>
                </div>
                <div>
                  <p className="text-sm text-muted-foreground">Country</p>
                  <p className="font-medium">{company.country || '-'}</p>
                </div>
                <div>
                  <p className="text-sm text-muted-foreground">Region</p>
                  <p className="font-medium">{company.region || '-'}</p>
                </div>
                <div>
                  <p className="text-sm text-muted-foreground">Brand Focus</p>
                  <p className="font-medium">{company.brand_focus || '-'}</p>
                </div>
                <div>
                  <p className="text-sm text-muted-foreground">Status</p>
                  <p className="font-medium">{company.status}</p>
                </div>
                <div>
                  <p className="text-sm text-muted-foreground">Source</p>
                  <p className="font-medium">{company.source || '-'}</p>
                </div>
              </div>
              {(company.domain || company.name) && (
                <div className="mt-4 pt-4 border-t">
                  <p className="text-sm text-muted-foreground mb-2">Links</p>
                  <div className="flex gap-4">
                    {company.domain && (
                      <a
                        href={`https://${company.domain}`}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-primary hover:underline"
                      >
                        Website
                      </a>
                    )}
                    <a
                      href={`https://www.linkedin.com/search/results/companies/?keywords=${encodeURIComponent(company.name)}`}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-primary hover:underline"
                    >
                      LinkedIn
                    </a>
                  </div>
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="contacts" className="space-y-4">
          {contactsLoading ? (
            <div>Loading contacts...</div>
          ) : (
            <div className="border rounded-lg">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Name</TableHead>
                    <TableHead>Email</TableHead>
                    <TableHead>Title</TableHead>
                    <TableHead>Confidence Score</TableHead>
                    <TableHead>Actions</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {contacts?.map((contact) => (
                    <TableRow key={contact.id}>
                      <TableCell className="font-medium">{contact.name}</TableCell>
                      <TableCell>{contact.email}</TableCell>
                      <TableCell>{contact.title || '-'}</TableCell>
                      <TableCell>
                        {contact.confidence_score
                          ? (contact.confidence_score * 100).toFixed(0) + '%'
                          : '-'}
                      </TableCell>
                      <TableCell>
                        <Link to={`/contacts/${contact.id}`}>
                          <button className="text-primary hover:underline">View</button>
                        </Link>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          )}
        </TabsContent>

        <TabsContent value="outreach" className="space-y-4">
          <div className="border rounded-lg">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Contact</TableHead>
                  <TableHead>Stage</TableHead>
                  <TableHead>Sent At</TableHead>
                  <TableHead>Opened At</TableHead>
                  <TableHead>Replied At</TableHead>
                  <TableHead>Status</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {companyOutreachLogs.map((log) => (
                  <TableRow key={log.id}>
                    <TableCell>
                      {log.contacts?.name || '-'}
                      <br />
                      <span className="text-sm text-muted-foreground">
                        {log.contacts?.email || '-'}
                      </span>
                    </TableCell>
                    <TableCell>Stage {log.sequence_stage}</TableCell>
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
                            : 'bg-gray-100 text-gray-800'
                        }`}
                      >
                        {log.status}
                      </span>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
        </TabsContent>
      </Tabs>
    </div>
  )
}

