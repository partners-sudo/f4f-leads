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

  const pendingReviews = reviews?.filter((r) => r.outcome === 'pending') || []

  return (
    <div className="p-6 space-y-6">
      <div>
        <h1 className="text-3xl font-bold">Interaction Reviews</h1>
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
        />
        <select
          className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
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
      ) : (
        <div className="border rounded-lg">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Contact</TableHead>
                <TableHead>Company</TableHead>
                <TableHead>Inbound Snippet</TableHead>
                <TableHead>Date of Reply</TableHead>
                <TableHead>Status</TableHead>
                <TableHead>Assigned To</TableHead>
                <TableHead>Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {reviews?.map((review) => (
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
                      <Button variant="outline" size="sm">Review</Button>
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

