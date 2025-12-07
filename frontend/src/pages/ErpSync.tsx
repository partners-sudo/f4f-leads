import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { supabase, type CrmToErpLog } from '@/lib/supabase'
import { n8nApi } from '@/lib/n8n'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import { Button } from '@/components/ui/button'
import { Link } from 'react-router-dom'

export default function ErpSync() {
  const queryClient = useQueryClient()

  const { data: syncLogs, isLoading } = useQuery({
    queryKey: ['erp-sync-logs'],
    queryFn: async () => {
      const { data, error } = await supabase
        .from('crm_to_erp_log')
        .select('*')
        .order('synced_at', { ascending: false })

      if (error) throw error
      
      // Fetch company names separately
      const logsWithCompanies = await Promise.all(
        (data || []).map(async (log) => {
          const { data: company } = await supabase
            .from('companies')
            .select('name')
            .eq('id', log.company_id)
            .single()
          
          return {
            ...log,
            company_name: company?.name || log.company_id,
          }
        })
      )
      
      return logsWithCompanies as (CrmToErpLog & { company_name: string })[]
    },
  })
  const [page, setPage] = useState(1)
  const pageSize = 10

  const totalItems = syncLogs?.length ?? 0
  const totalPages = Math.max(1, Math.ceil(totalItems / pageSize))
  const start = (page - 1) * pageSize
  const end = start + pageSize
  const paginatedSyncLogs = syncLogs?.slice(start, end) ?? []

  const syncMutation = useMutation({
    mutationFn: async (companyId: string) => {
      return n8nApi.syncToErp({ company_id: companyId })
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['erp-sync-logs'] })
    },
  })

  const handleSync = (companyId: string) => {
    if (confirm('Sync this company to ERP?')) {
      syncMutation.mutate(companyId)
    }
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold pb-6">ERP Sync Log</h1>
        <p className="text-muted-foreground">
          Historical syncs to ERP/Retool
        </p>
      </div>

      {isLoading ? (
        <div>Loading...</div>
      ) : !syncLogs || syncLogs.length === 0 ? (
        <div className="text-center py-8 text-muted-foreground">No ERP sync logs found</div>
      ) : (
        <div className="border rounded-lg bg-card/60">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Company</TableHead>
                <TableHead>Synced At</TableHead>
                <TableHead>Payload</TableHead>
                <TableHead>Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {paginatedSyncLogs.map((log) => (
                <TableRow key={log.id}>
                  <TableCell className="font-medium">
                    <Link
                      to={`/companies/${log.company_id}`}
                      className="text-primary hover:underline"
                    >
                      {log.company_name || log.company_id}
                    </Link>
                  </TableCell>
                  <TableCell>
                    {new Date(log.synced_at).toLocaleString()}
                  </TableCell>
                  <TableCell className="max-w-xs truncate">
                    {JSON.stringify(log.payload)}
                  </TableCell>
                  <TableCell>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => handleSync(log.company_id)}
                      disabled={syncMutation.isPending}
                    >
                      Re-sync
                    </Button>
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

