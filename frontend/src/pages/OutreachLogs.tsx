import { useState } from 'react'
import { useOutreachLogs } from '@/hooks/useOutreachLogs'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import { Input } from '@/components/ui/input'

export default function OutreachLogs() {
  const [filters, setFilters] = useState({
    stage: '',
    brand: '',
    status: '',
    dateFrom: '',
    dateTo: '',
  })

  const { data: logs, isLoading, error } = useOutreachLogs(filters)
  const [page, setPage] = useState(1)
  const pageSize = 6

  const totalItems = logs?.length ?? 0
  const totalPages = Math.max(1, Math.ceil(totalItems / pageSize))
  const start = (page - 1) * pageSize
  const end = start + pageSize
  const paginatedLogs = logs?.slice(start, end) ?? []

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold pb-6">Outreach Logs</h1>
        <p className="text-muted-foreground">All email outreach activity</p>
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4">
          <p className="text-red-800 font-medium">Error loading outreach logs</p>
          <p className="text-red-600 text-sm mt-1">
            {error instanceof Error ? error.message : 'Unknown error occurred'}
          </p>
          <p className="text-red-500 text-xs mt-2">
            Check browser console for details. This might be a foreign key relationship issue.
          </p>
        </div>
      )}

      {/* Filters */}
      <div className="grid grid-cols-5 gap-4">
        <Input
          type="number"
          placeholder="Stage (0, 1, 2)"
          value={filters.stage}
          onChange={(e) => setFilters({ ...filters, stage: e.target.value })}
        />
        <Input
          placeholder="Brand"
          value={filters.brand}
          onChange={(e) => setFilters({ ...filters, brand: e.target.value })}
        />
        <select
          className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
          value={filters.status}
          onChange={(e) => setFilters({ ...filters, status: e.target.value })}
        >
          <option value="">All Status</option>
          <option value="sent">Sent</option>
          <option value="replied">Replied</option>
          <option value="bounced">Bounced</option>
          <option value="failed">Failed</option>
          <option value="stopped">Stopped</option>
        </select>
        <Input
          type="date"
          placeholder="From Date"
          value={filters.dateFrom}
          onChange={(e) => setFilters({ ...filters, dateFrom: e.target.value })}
        />
        <Input
          type="date"
          placeholder="To Date"
          value={filters.dateTo}
          onChange={(e) => setFilters({ ...filters, dateTo: e.target.value })}
        />
      </div>

      {/* Table */}
      {isLoading ? (
        <div className="text-center py-8">Loading outreach logs...</div>
      ) : error ? (
        <div className="text-center py-8 text-muted-foreground">
          Unable to load outreach logs. Please check the error message above.
        </div>
      ) : !logs || logs.length === 0 ? (
        <div className="text-center py-8 text-muted-foreground">
          <p className="text-lg font-medium mb-2">No outreach logs found</p>
          <p className="text-sm">
            {Object.values(filters).some(f => f) 
              ? 'Try adjusting your filters' 
              : 'No outreach activity recorded yet'}
          </p>
        </div>
      ) : (
        <div className="border rounded-lg bg-card/60">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Contact</TableHead>
                <TableHead>Company</TableHead>
                <TableHead>Email Snippet</TableHead>
                <TableHead>Stage</TableHead>
                <TableHead>Sent At</TableHead>
                <TableHead>Replied At</TableHead>
                <TableHead>Status</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {paginatedLogs.map((log) => (
                <TableRow key={log.id}>
                  <TableCell>
                    {log.contacts?.name || '-'}
                    <br />
                    <span className="text-sm text-muted-foreground">
                      {log.contacts?.email || '-'}
                    </span>
                  </TableCell>
                  <TableCell>{log.companies?.name || '-'}</TableCell>
                  <TableCell className="max-w-xs truncate">
                    {log.message_snippet || '-'}
                  </TableCell>
                  <TableCell>Stage {log.sequence_stage}</TableCell>
                  <TableCell>
                    {log.sent_at
                      ? new Date(log.sent_at).toLocaleString()
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

