import { useQuery } from '@tanstack/react-query'
import { supabase, type MergeCandidate } from '@/lib/supabase'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import { Button } from '@/components/ui/button'

export default function MergeCandidates() {
  const { data: candidates, isLoading } = useQuery({
    queryKey: ['merge-candidates'],
    queryFn: async () => {
      const { data, error } = await supabase
        .from('merge_candidates')
        .select('*')
        .order('score', { ascending: false })

      if (error) throw error
      
      // Fetch company names separately if needed
      const candidatesWithNames = await Promise.all(
        (data || []).map(async (candidate) => {
          const [companyA, companyB] = await Promise.all([
            supabase.from('companies').select('name').eq('id', candidate.company_a).single(),
            supabase.from('companies').select('name').eq('id', candidate.company_b).single(),
          ])
          
          return {
            ...candidate,
            company_a_name: companyA.data?.name || candidate.company_a,
            company_b_name: companyB.data?.name || candidate.company_b,
          }
        })
      )
      
      return candidatesWithNames as (MergeCandidate & {
        company_a_name: string
        company_b_name: string
      })[]
    },
  })

  return (
    <div className="p-6 space-y-6">
      <div>
        <h1 className="text-3xl font-bold">Merge Candidates</h1>
        <p className="text-muted-foreground">
          Potential duplicate companies to merge
        </p>
      </div>

      {isLoading ? (
        <div>Loading...</div>
      ) : (
        <div className="border rounded-lg">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Company A</TableHead>
                <TableHead>Company B</TableHead>
                <TableHead>Score</TableHead>
                <TableHead>Created</TableHead>
                <TableHead>Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {candidates?.map((candidate) => (
                <TableRow key={candidate.id}>
                  <TableCell className="font-medium">
                    {candidate.company_a_name || candidate.company_a}
                  </TableCell>
                  <TableCell className="font-medium">
                    {candidate.company_b_name || candidate.company_b}
                  </TableCell>
                  <TableCell>
                    <span className="px-2 py-1 bg-blue-100 text-blue-800 rounded text-xs">
                      {(candidate.score * 100).toFixed(0)}%
                    </span>
                  </TableCell>
                  <TableCell>
                    {new Date(candidate.created_at).toLocaleDateString()}
                  </TableCell>
                  <TableCell>
                    <Button variant="outline" size="sm" disabled>
                      Mark as Merged (Future)
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

