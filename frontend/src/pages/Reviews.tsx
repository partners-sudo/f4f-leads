import { useState } from 'react'
import { Link } from 'react-router-dom'
import { useInteractionReviews } from '@/hooks/useInteractionReviews'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'

export default function Reviews() {
  const [filters, setFilters] = useState({
    assigned_to: '',
    outcome: '',
    date: '',
  })

  const { data: reviews, isLoading } = useInteractionReviews(filters)
  const [page, setPage] = useState(1)
  const pageSize = 8

  const totalItems = reviews?.length ?? 0
  const totalPages = Math.max(1, Math.ceil(totalItems / pageSize))
  const start = (page - 1) * pageSize
  const end = start + pageSize
  const paginatedReviews = reviews?.slice(start, end) ?? []

  const pendingReviews = reviews?.filter((r) => r.outcome === 'pending') || []

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold pb-6">Interaction Reviews</h1>
        <p className="text-muted-foreground">
          Review and respond to contact replies
        </p>
      </div>

      {/* Filters */}
      <div className="grid grid-cols-3 gap-4">
        <Input
          placeholder="Assigned To"
          value={filters.assigned_to}
          onChange={(e) =>
            setFilters({ ...filters, assigned_to: e.target.value })
          }                      
          className='bg-card/20 text-foreground'
        />
        <select
          className="flex h-10 w-full rounded-md border border-input px-3 py-2 text-sm bg-card/20 text-foreground"
          value={filters.outcome}
          onChange={(e) => setFilters({ ...filters, outcome: e.target.value })}
        >
          <option value="">All Outcomes</option>
          <option value="pending">Pending</option>
          <option value="f4f">F4F</option>
          <option value="figgyz">FiGGYZ</option>
          <option value="not_interested">Not Interested</option>
          <option value="converted">Converted</option>
        </select>
        <Input
          type="date"
          placeholder="Date"
          value={filters.date}
          onChange={(e) => setFilters({ ...filters, date: e.target.value })}                        
          className='bg-card/20 text-foreground'
        />
      </div>

      {/* Pending Reviews Alert */}
      {pendingReviews.length > 0 && (
        <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
          <p className="font-medium text-yellow-800">
            {pendingReviews.length} pending review{pendingReviews.length !== 1 ? 's' : ''}
          </p>
        </div>
      )}

      {/* Table */}
      {isLoading ? (
        <div>Loading...</div>
      ) : !reviews || reviews.length === 0 ? (
        <div className="text-center py-8 text-muted-foreground">No interaction reviews found</div>
      ) : (
        <div className="border rounded-lg">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Contact</TableHead>
                <TableHead>Company</TableHead>
                <TableHead>Inbound Snippet</TableHead>
                <TableHead>Date of Reply</TableHead>
                <TableHead>Outcome</TableHead>
                <TableHead>Assigned To</TableHead>
                <TableHead>Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {paginatedReviews.map((review) => (
                <TableRow key={review.id}>
                  <TableCell>
                    {review.outreach_logs?.contacts?.name || '-'}
                    <br />
                    <span className="text-sm text-muted-foreground">
                      {review.outreach_logs?.contacts?.email || '-'}
                    </span>
                  </TableCell>
                  <TableCell>
                    {review.outreach_logs?.companies?.name || '-'}
                  </TableCell>
                  <TableCell className="max-w-xs truncate">
                    {review.notes || '-'}
                  </TableCell>
                  <TableCell>
                    {new Date(review.created_at).toLocaleString()}
                  </TableCell>
                  <TableCell>
                    <span
                      className={`px-2 py-1 rounded text-xs ${
                        review.outcome === 'pending'
                          ? 'bg-yellow-100 text-yellow-800'
                          : review.outcome === 'converted'
                          ? 'bg-green-100 text-green-800'
                          : 'bg-gray-100 text-gray-800'
                      }`}
                    >
                      {review.outcome}
                    </span>
                  </TableCell>
                  <TableCell>{review.assigned_to || '-'}</TableCell>
                  <TableCell>
                    <Link to={`/reviews/${review.id}`}>
                      <Button variant="outline" size="sm" className='bg-transparent'>Review</Button>
                    </Link>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
          <div className="flex items-center justify-between border-t px-4 py-3 text-xs text-muted-foreground">
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

