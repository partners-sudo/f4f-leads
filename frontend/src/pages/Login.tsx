import { useState } from 'react'
import { useAuth } from '@/hooks/useAuth'
import { useNavigate } from 'react-router-dom'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'

export default function Login() {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const [isSignUp, setIsSignUp] = useState(false)
  const { signIn, signUp } = useAuth()
  const navigate = useNavigate()

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    setLoading(true)

    try {
      if (isSignUp) {
        await signUp(email, password)
        setError('Account created! Please check your email to confirm your account, or sign in if email confirmation is disabled.')
      } else {
        await signIn(email, password)
        navigate('/dashboard')
      }
    } catch (err: any) {
      setError(err.message || `Failed to ${isSignUp ? 'sign up' : 'sign in'}`)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-950 via-slate-900 to-slate-950 flex items-center justify-center px-4 py-10">
      <div className="w-full max-w-6xl grid gap-10 md:grid-cols-[minmax(0,1.1fr)_minmax(0,1fr)] items-center">
        <div className="hidden md:flex flex-col gap-6 text-slate-100">
          <span className="inline-flex items-center gap-2 rounded-full border border-white/10 bg-white/5 px-3 py-1 text-24 font-medium tracking-[0.16em] uppercase backdrop-blur">
            <span className="h-1.5 w-1.5 rounded-full bg-emerald-400 animate-pulse" />
            F4F + FiGGYZ CRM
          </span>
          <h1 className="text-3xl lg:text-4xl font-semibold leading-tight">
            Lead discovery, outreach, and reviews
            <span className="block bg-gradient-to-r from-emerald-300 via-sky-300 to-indigo-300 bg-clip-text text-transparent">
              in one focused console.
            </span>
          </h1>
          <p className="max-w-md text-sm text-slate-300/80">
            Securely sign in to access your scraping console, enrichment tools, and pipeline views.
          </p>
          <div className="flex flex-wrap gap-3 text-xs text-slate-300/80">
            <div className="inline-flex items-center gap-2 rounded-full border border-white/10 bg-white/5 px-3 py-1 backdrop-blur-sm">
              <span className="h-1.5 w-1.5 rounded-full bg-emerald-400" />
              Live syncing
            </div>
            <div className="inline-flex items-center gap-2 rounded-full border border-white/10 bg-white/5 px-3 py-1 backdrop-blur-sm">
              <span className="h-1.5 w-1.5 rounded-full bg-sky-400" />
              Scraping console
            </div>
            <div className="inline-flex items-center gap-2 rounded-full border border-white/10 bg-white/5 px-3 py-1 backdrop-blur-sm">
              <span className="h-1.5 w-1.5 rounded-full bg-indigo-400" />
              Outreach & reviews
            </div>
          </div>
        </div>

        <Card className="relative w-full max-w-md mx-auto border-white/10 bg-slate-900/60 text-slate-100 shadow-[0_18px_45px_rgba(15,23,42,0.9)] backdrop-blur-2xl transition-transform duration-500 ease-out motion-safe:hover:-translate-y-1">
          <div className="pointer-events-none absolute inset-px rounded-[--radius] border border-white/5" />
          <CardHeader className="space-y-2 pb-4">
            <CardTitle className="text-xl font-semibold tracking-tight flex items-center justify-between">
              <span>{isSignUp ? 'Create your account' : 'Welcome back'}</span>
              <span className="text-[0.7rem] font-medium text-emerald-300/90 bg-emerald-500/10 px-2 py-1 rounded-full border border-emerald-400/30">
                F4F + FiGGYZ CRM
              </span>
            </CardTitle>
            <CardDescription className="text-xs text-slate-300">
              {isSignUp ? 'Create a new account to start managing leads, outreach, and reviews.' : 'Sign in with your credentials to continue where you left off.'}
            </CardDescription>
          </CardHeader>
          <CardContent className="pb-6">
            <form onSubmit={handleSubmit} className="space-y-5">
              <div className="space-y-2">
                <Label htmlFor="email" className="text-xs font-medium text-slate-200">
                  Email
                </Label>
                <Input
                  id="email"
                  type="email"
                  placeholder="you@example.com"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  required
                  className="h-10 border-slate-700/60 bg-slate-900/60 text-sm placeholder:text-slate-500 focus-visible:ring-1 focus-visible:ring-emerald-400/80 focus-visible:border-emerald-400/80 transition-colors"
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="password" className="text-xs font-medium text-slate-200">
                  Password
                </Label>
                <Input
                  id="password"
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  required
                  minLength={6}
                  className="h-10 border-slate-700/60 bg-slate-900/60 text-sm placeholder:text-slate-500 focus-visible:ring-1 focus-visible:ring-emerald-400/80 focus-visible:border-emerald-400/80 transition-colors"
                />
              </div>
              {error && (
                <div
                  className={`text-xs rounded-md border px-3 py-2 shadow-sm backdrop-blur-sm transition-colors ${error.includes('created')
                    ? 'border-emerald-500/40 bg-emerald-500/10 text-emerald-300'
                    : 'border-red-500/40 bg-red-500/10 text-red-300'
                  }`}
                >
                  {error}
                </div>
              )}
              <Button
                type="submit"
                className="w-full h-10 text-sm font-medium tracking-wide rounded-md bg-gradient-to-r from-emerald-400 via-sky-400 to-indigo-400 text-slate-950 shadow-[0_14px_30px_rgba(8,47,73,0.75)] transition-all duration-200 ease-out hover:brightness-110 hover:shadow-[0_20px_40px_rgba(8,47,73,0.9)] disabled:cursor-not-allowed disabled:opacity-70"
                disabled={loading}
              >
                {loading
                  ? isSignUp
                    ? 'Creating account...'
                    : 'Signing in...'
                  : isSignUp
                  ? 'Sign Up'
                  : 'Sign In'}
              </Button>
              <div className="pt-1 text-center text-xs text-slate-300/90">
                <span className="mr-1 text-slate-400">
                  {isSignUp ? 'Already have an account?' : "Don't have an account?"}
                </span>
                <button
                  type="button"
                  onClick={() => {
                    setIsSignUp(!isSignUp)
                    setError('')
                  }}
                  className="font-medium text-emerald-300 hover:text-emerald-200 hover:underline underline-offset-4 transition-colors"
                >
                  {isSignUp ? 'Sign in' : 'Sign up'}
                </button>
              </div>
            </form>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
