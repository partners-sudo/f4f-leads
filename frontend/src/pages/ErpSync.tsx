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
    <div className="p-6 space-y-6">
      <div>
        <h1 className="text-3xl font-bold">ERP Sync Log</h1>
        <p className="text-muted-foreground">
          Historical syncs to ERP/Retool
        </p>
      </div>

      {isLoading ? (
        <div>Loading...</div>
      ) : (
        <div className="border rounded-lg">
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
              {syncLogs?.map((log) => (
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
        </div>
      )}
    </div>
  )
}

