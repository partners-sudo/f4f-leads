import { useState } from 'react'
import { Link } from 'react-router-dom'
import { useCompanies } from '@/hooks/useCompanies'
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
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'

export default function Companies() {
  const [filters, setFilters] = useState({
    region: '',
    country: '',
    brand_focus: '',
    status: '',
    source: '',
  })

  const { data: companies, isLoading, error } = useCompanies(filters)
  const [page, setPage] = useState(1)
  const pageSize = 8

  const totalItems = companies?.length ?? 0
  const totalPages = Math.max(1, Math.ceil(totalItems / pageSize))
  const start = (page - 1) * pageSize
  const end = start + pageSize
  const paginatedCompanies = companies?.slice(start, end) ?? []

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold pb-6">Companies</h1>
          <p className="text-muted-foreground pb-1">Manage all companies</p>
        </div>
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4">
          <p className="text-red-800 font-medium">Error loading companies</p>
          <p className="text-red-600 text-sm mt-1">
            {error instanceof Error ? error.message : 'Unknown error occurred'}
          </p>
          <p className="text-red-500 text-xs mt-2">
            Check browser console for details. This might be a Row Level Security (RLS) policy issue.
          </p>
        </div>
      )}

      {/* Filters */}
      <div className="grid grid-cols-5 gap-4">
        <Input
          placeholder="Region"
          value={filters.region}
          onChange={(e) => setFilters({ ...filters, region: e.target.value })}
          className='bg-card/20 text-foreground'
        />
        <Input
          placeholder="Country"
          value={filters.country}
          onChange={(e) => setFilters({ ...filters, country: e.target.value })}
          className='bg-card/20 text-foreground'
        />
        <Input
          placeholder="Brand Focus"
          value={filters.brand_focus}
          onChange={(e) => setFilters({ ...filters, brand_focus: e.target.value })}
          className='bg-card/20 text-foreground'
        />
        <select
          className="flex h-10 w-full rounded-md border border-input bg-card/20 text-foreground px-3 py-2 text-sm"
          value={filters.status}
          onChange={(e) => setFilters({ ...filters, status: e.target.value })}
        >
          <option value="">All Status</option>
          <option value="new">New</option>
          <option value="active">Active</option>
          <option value="merged">Merged</option>
          <option value="cold">Cold</option>
        </select>
        <select
          className="flex h-10 w-full rounded-md border border-input bg-card/20 text-foreground px-3 py-2 text-sm"
          value={filters.source}
          onChange={(e) => setFilters({ ...filters, source: e.target.value })}
        >
          <option value="">All Sources</option>
          <option value="scraper">Scraper</option>
          <option value="manual">Manual</option>
        </select>
      </div>

      {/* Table */}
      {isLoading ? (
        <div className="text-center py-8">Loading companies...</div>
      ) : error ? (
        <div className="text-center py-8 text-muted-foreground">
          Unable to load companies. Please check the error message above.
        </div>
      ) : !companies || companies.length === 0 ? (
        <div className="text-center py-8 text-muted-foreground">
          <p className="text-lg font-medium mb-2">No companies found</p>
          <p className="text-sm">
            {Object.values(filters).some(f => f) 
              ? 'Try adjusting your filters' 
              : 'No companies in the database yet'}
          </p>
        </div>
      ) : (
        <div className="border rounded-lg">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Name</TableHead>
                <TableHead>Domain</TableHead>
                <TableHead>Region</TableHead>
                <TableHead>Brand Focus</TableHead>
                <TableHead>Status</TableHead>
                <TableHead>Created</TableHead>
                <TableHead>Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {paginatedCompanies.map((company) => (
                <TableRow key={company.id}>
                  <TableCell className="font-medium">{company.name}</TableCell>
                  <TableCell>{company.domain || '-'}</TableCell>
                  <TableCell>{company.region || '-'}</TableCell>
                  <TableCell>{company.brand_focus || '-'}</TableCell>
                  <TableCell>
                    <span className={`px-2 py-1 rounded text-xs ${
                      company.status === 'active' ? 'bg-green-100 text-green-800' :
                      company.status === 'new' ? 'bg-blue-100 text-blue-800' :
                      company.status === 'cold' ? 'bg-gray-100 text-gray-800' :
                      'bg-yellow-100 text-yellow-800'
                    }`}>
                      {company.status}
                    </span>
                  </TableCell>
                  <TableCell>
                    {new Date(company.created_at).toLocaleDateString()}
                  </TableCell>
                  <TableCell>
                    <Link to={`/companies/${company.id}`}>
                      <Button variant="outline" className='bg-transparent' size="sm">View</Button>
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

