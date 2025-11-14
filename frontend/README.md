# F4F + FiGGYZ CRM Frontend

React-based CRM application for managing leads, outreach, and customer interactions.

## Setup

1. Install dependencies:
```bash
npm install
```

2. Create a `.env` file in the root of the `frontend` directory with the following variables:

```env
VITE_SUPABASE_URL=your_supabase_project_url
VITE_SUPABASE_ANON_KEY=your_supabase_anon_key
VITE_N8N_BASE_URL=your_n8n_workflow_base_url
```

**Environment Variables:**
- `VITE_SUPABASE_URL`: Your Supabase project URL (e.g., `https://xxxxx.supabase.co`)
- `VITE_SUPABASE_ANON_KEY`: Your Supabase anonymous/public key
- `VITE_N8N_BASE_URL`: Your n8n webhook base URL (e.g., `https://your-n8n-instance.com/webhook`)

4. Start the development server:
```bash
npm run dev
```

## Features

- **Dashboard**: Overview of CRM metrics and KPIs
- **Companies**: Manage and view all companies
- **Contacts**: Manage and view all contacts
- **Outreach Logs**: Track all email outreach activity
- **Interaction Reviews**: Review and respond to contact replies with AI suggestions
- **Templates**: Manage email templates for outreach sequences
- **Merge Candidates**: View potential duplicate companies
- **ERP Sync**: Sync converted leads to ERP/Retool

## Tech Stack

- React 19
- TypeScript
- Vite
- Tailwind CSS
- Supabase (Database + Auth)
- React Query (Data fetching)
- React Router (Routing)
- shadcn/ui components

## Project Structure

```
src/
  components/
    ui/          # shadcn/ui components
    Layout.tsx   # Main layout with navigation
  pages/         # All page components
  hooks/         # Custom React hooks for data fetching
  lib/           # Utilities (Supabase client, n8n API, etc.)
```

## Development

The app uses:
- React Query for server state management
- Supabase Realtime (optional) for live updates
- Protected routes with authentication
- Type-safe API calls with TypeScript
