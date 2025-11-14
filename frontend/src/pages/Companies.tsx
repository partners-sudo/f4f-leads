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

  const { data: companies, isLoading } = useCompanies(filters)

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">Companies</h1>
          <p className="text-muted-foreground">Manage all companies</p>
        </div>
      </div>

      {/* Filters */}
      <div className="grid grid-cols-5 gap-4">
        <Input
          placeholder="Region"
          value={filters.region}
          onChange={(e) => setFilters({ ...filters, region: e.target.value })}
        />
        <Input
          placeholder="Country"
          value={filters.country}
          onChange={(e) => setFilters({ ...filters, country: e.target.value })}
        />
        <Input
          placeholder="Brand Focus"
          value={filters.brand_focus}
          onChange={(e) => setFilters({ ...filters, brand_focus: e.target.value })}
        />
        <select
          className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
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
          className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
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
        <div>Loading...</div>
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
              {companies?.map((company) => (
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

