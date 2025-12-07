import { useState } from 'react'
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
  const [page, setPage] = useState(1)
  const pageSize = 9

  const totalItems = contacts?.length ?? 0
  const totalPages = Math.max(1, Math.ceil(totalItems / pageSize))
  const start = (page - 1) * pageSize
  const end = start + pageSize
  const paginatedContacts = contacts?.slice(start, end) ?? []

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold pb-3">Contacts</h1>
        <p className="text-muted-foreground pb-3">Manage all contacts</p>
      </div>

      {isLoading ? (
        <div>Loading...</div>
      ) : !contacts || contacts.length === 0 ? (
        <div className="text-center py-8 text-muted-foreground">No contacts found</div>
      ) : (
        <div className="border rounded-lg bg-card/60">
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
              {paginatedContacts.map((contact) => (
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
          <div className="flex items-center justify-between border-t px-4 py-3 text-xs text-muted-foreground bg-background/40">
            <span>
              Showing <span className="font-medium">{start + 1}</span>–
              <span className="font-medium">{Math.min(end, totalItems)}</span> of{' '}
              <span className="font-medium">{totalItems}</span>
            </span>
            <div className="flex items-center gap-2">
              <button
                type="button"
                onClick={() => setPage((p) => Math.max(1, p - 1))}
                disabled={page === 1}
                className="inline-flex items-center rounded-md border px-2 py-1 text-[0.7rem] font-medium disabled:opacity-40 disabled:cursor-not-allowed hover:bg-accent"
              >
                Prev
              </button>
              <span>
                Page <span className="font-semibold">{page}</span> of{' '}
                <span className="font-semibold">{totalPages}</span>
              </span>
              <button
                type="button"
                onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                disabled={page === totalPages}
                className="inline-flex items-center rounded-md border px-2 py-1 text-[0.7rem] font-medium disabled:opacity-40 disabled:cursor-not-allowed hover:bg-accent"
              >
                Next
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

