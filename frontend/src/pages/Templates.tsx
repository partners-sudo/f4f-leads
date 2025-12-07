import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { supabase, type Template } from '@/lib/supabase'
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
import { Label } from '@/components/ui/label'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog'

export default function Templates() {
  const [isDialogOpen, setIsDialogOpen] = useState(false)
  const [editingTemplate, setEditingTemplate] = useState<Template | null>(null)
  const [formData, setFormData] = useState({
    name: '',
    brand: '',
    subject: '',
    body: '',
    variables: '',
  })

  const queryClient = useQueryClient()

  const { data: templates, isLoading } = useQuery({
    queryKey: ['templates'],
    queryFn: async () => {
      const { data, error } = await supabase
        .from('templates')
        .select('*')
        .order('created_at', { ascending: false })

      if (error) throw error
      return data as Template[]
    },
  })
  const [page, setPage] = useState(1)
  const pageSize = 9

  const totalItems = templates?.length ?? 0
  const totalPages = Math.max(1, Math.ceil(totalItems / pageSize))
  const start = (page - 1) * pageSize
  const end = start + pageSize
  const paginatedTemplates = templates?.slice(start, end) ?? []

  const createMutation = useMutation({
    mutationFn: async (data: typeof formData) => {
      const { error } = await supabase.from('templates').insert({
        name: data.name,
        brand: data.brand,
        subject: data.subject,
        body: data.body,
        variables: data.variables || null,
      })
      if (error) throw error
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['templates'] })
      setIsDialogOpen(false)
      setFormData({ name: '', brand: '', subject: '', body: '', variables: '' })
    },
  })

  const updateMutation = useMutation({
    mutationFn: async ({ id, data }: { id: string; data: typeof formData }) => {
      if (!id) {
        throw new Error('Template ID is required for update')
      }
      
      // Use upsert instead of update to avoid CORS PATCH issue
      // Upsert with ID will update if exists (uses POST method which works)
      const { error } = await supabase
        .from('templates')
        .upsert({
          id: id,
          name: data.name,
          brand: data.brand,
          subject: data.subject,
          body: data.body,
          variables: data.variables || null,
        })
      
      if (error) {
        console.error('Failed to update template:', error)
        throw error
      }
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['templates'] })
      setIsDialogOpen(false)
      setEditingTemplate(null)
      setFormData({ name: '', brand: '', subject: '', body: '', variables: '' })
    },
    onError: (error: any) => {
      console.error('Failed to update template:', error)
      const errorMessage = error?.message || error?.toString() || 'Unknown error'
      alert(`Failed to update template: ${errorMessage}`)
    },
  })

  const deleteMutation = useMutation({
    mutationFn: async (id: string) => {
      const { error } = await supabase.from('templates').delete().eq('id', id)
      if (error) throw error
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['templates'] })
    },
  })

  const handleEdit = (template: Template) => {
    setEditingTemplate(template)
    setFormData({
      name: template.name,
      brand: template.brand,
      subject: template.subject,
      body: template.body,
      variables: template.variables || '',
    })
    setIsDialogOpen(true)
  }

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (editingTemplate) {
      updateMutation.mutate({ id: editingTemplate.id, data: formData })
    } else {
      createMutation.mutate(formData)
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold pb-6">Templates</h1>
          <p className="text-muted-foreground">Manage email templates</p>
        </div>
        <Dialog 
          open={isDialogOpen} 
          onOpenChange={(open) => {
            setIsDialogOpen(open)
            if (!open) {
              setEditingTemplate(null)
              setFormData({ name: '', brand: '', subject: '', body: '', variables: '' })
            }
          }}
        >
          <DialogTrigger asChild>
            <Button onClick={() => {
              setEditingTemplate(null)
              setFormData({ name: '', brand: '', subject: '', body: '', variables: '' })
            }}>
              Add Template
            </Button>
          </DialogTrigger>
          <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
            <DialogHeader>
              <DialogTitle>
                {editingTemplate ? 'Edit Template' : 'Add Template'}
              </DialogTitle>
              <DialogDescription>
                Create or edit an email template for outreach sequences
              </DialogDescription>
            </DialogHeader>
            <form onSubmit={handleSubmit} className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="name">Name</Label>
                <Input
                  id="name"
                  value={formData.name}
                  onChange={(e) =>
                    setFormData({ ...formData, name: e.target.value })
                  }
                  required
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="brand">Brand</Label>
                <select
                  id="brand"
                  className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
                  value={formData.brand}
                  onChange={(e) =>
                    setFormData({ ...formData, brand: e.target.value })
                  }
                  required
                >
                  <option value="">Select brand</option>
                  <option value="F4F">F4F</option>
                  <option value="FiGGYZ">FiGGYZ</option>
                </select>
              </div>
              <div className="space-y-2">
                <Label htmlFor="subject">Subject</Label>
                <Input
                  id="subject"
                  value={formData.subject}
                  onChange={(e) =>
                    setFormData({ ...formData, subject: e.target.value })
                  }
                  required
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="body">Body</Label>
                <textarea
                  id="body"
                  className="flex min-h-[200px] w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
                  value={formData.body}
                  onChange={(e) =>
                    setFormData({ ...formData, body: e.target.value })
                  }
                  required
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="variables">Variables (comma-separated)</Label>
                <Input
                  id="variables"
                  value={formData.variables}
                  onChange={(e) =>
                    setFormData({ ...formData, variables: e.target.value })
                  }
                  placeholder="e.g., {{name}}, {{company}}"
                />
              </div>
              <div className="flex gap-2">
                <Button 
                  type="submit"
                  disabled={editingTemplate ? updateMutation.isPending : createMutation.isPending}
                >
                  {editingTemplate 
                    ? (updateMutation.isPending ? 'Updating...' : 'Update')
                    : (createMutation.isPending ? 'Creating...' : 'Create')
                  }
                </Button>
                <Button
                  type="button"
                  variant="outline"
                  onClick={() => setIsDialogOpen(false)}
                >
                  Cancel
                </Button>
              </div>
            </form>
          </DialogContent>
        </Dialog>
      </div>

      {isLoading ? (
        <div>Loading...</div>
      ) : !templates || templates.length === 0 ? (
        <div className="text-center py-8 text-muted-foreground">No templates found</div>
      ) : (
        <div className="border rounded-lg">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Name</TableHead>
                <TableHead>Brand</TableHead>
                <TableHead>Subject</TableHead>
                <TableHead>Created</TableHead>
                <TableHead>Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {paginatedTemplates.map((template) => (
                <TableRow key={template.id}>
                  <TableCell className="font-medium">{template.name}</TableCell>
                  <TableCell>{template.brand}</TableCell>
                  <TableCell>{template.subject}</TableCell>
                  <TableCell>
                    {new Date(template.created_at).toLocaleDateString()}
                  </TableCell>
                  <TableCell>
                    <div className="flex gap-2">
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => handleEdit(template)}
                        className='bg-transparent'
                      >
                        Edit
                      </Button>
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => {
                          if (
                            confirm(
                              'Are you sure you want to delete this template?'
                            )
                          ) {
                            deleteMutation.mutate(template.id)
                          }
                        }}
                        className='bg-transparent'
                      >
                        Delete
                      </Button>
                    </div>
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

