import { Link } from 'react-router-dom'
import { useContacts } from '@/hooks/useContacts'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import { Button } from '@/components/ui/button'

export default function Contacts() {
  const { data: contacts, isLoading } = useContacts()

  return (
    <div className="p-6 space-y-6">
      <div>
        <h1 className="text-3xl font-bold">Contacts</h1>
        <p className="text-muted-foreground">Manage all contacts</p>
      </div>

      {isLoading ? (
        <div>Loading...</div>
      ) : (
        <div className="border rounded-lg">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Name</TableHead>
                <TableHead>Email</TableHead>
                <TableHead>Company</TableHead>
                <TableHead>Title</TableHead>
                <TableHead>Confidence Score</TableHead>
                <TableHead>Last Validated</TableHead>
                <TableHead>Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {contacts?.map((contact) => (
                <TableRow key={contact.id}>
                  <TableCell className="font-medium">{contact.name}</TableCell>
                  <TableCell>{contact.email}</TableCell>
                  <TableCell>
                    <Link
                      to={`/companies/${contact.company_id}`}
                      className="text-primary hover:underline"
                    >
                      {(contact as any).company?.name || 'View Company'}
                    </Link>
                  </TableCell>
                  <TableCell>{contact.title || '-'}</TableCell>
                  <TableCell>
                    {contact.confidence_score
                      ? (contact.confidence_score * 100).toFixed(0) + '%'
                      : '-'}
                  </TableCell>
                  <TableCell>
                    {contact.last_validated
                      ? new Date(contact.last_validated).toLocaleDateString()
                      : '-'}
                  </TableCell>
                  <TableCell>
                    <Link to={`/contacts/${contact.id}`}>
                      <Button variant="outline" size="sm">View</Button>
                    </Link>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      )}
    </div>
  )
}

