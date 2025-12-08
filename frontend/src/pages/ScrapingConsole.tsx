import { useEffect, useRef, useState } from 'react'
import type { ScrapeResult } from '@/lib/finder'
import { FINDER_BASE_URL } from '@/lib/finder'

function ScrapingConsole() {
  const [linkedinKeyword, setLinkedinKeyword] = useState('retail buyer')
  const [competitorBrands, setCompetitorBrands] = useState('Funko, Tubbz, Cable guys')
  const [csvPath, setCsvPath] = useState('')
  const csvSource = 'csv_upload'

  const [activeTab, setActiveTab] = useState<'linkedin' | 'competitors' | 'csv'>('linkedin')

  const [linkedinResult, setLinkedinResult] = useState<ScrapeResult | null>(null)
  const [competitorResult, setCompetitorResult] = useState<ScrapeResult | null>(null)
  const [csvResult, setCsvResult] = useState<ScrapeResult | null>(null)
  const [linkedinRunId, setLinkedinRunId] = useState<string | null>(null)
  const [competitorRunId, setCompetitorRunId] = useState<string | null>(null)
  const [csvRunId, setCsvRunId] = useState<string | null>(null)
  const [linkedinPaused, setLinkedinPaused] = useState(false)
  const [competitorPaused, setCompetitorPaused] = useState(false)
  const [csvPaused, setCsvPaused] = useState(false)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const linkedinLogRef = useRef<HTMLPreElement | null>(null)
  const competitorLogRef = useRef<HTMLPreElement | null>(null)
  const csvLogRef = useRef<HTMLPreElement | null>(null)

  const linkedinSourceRef = useRef<EventSource | null>(null)
  const competitorSourceRef = useRef<EventSource | null>(null)
  const csvSourceRef = useRef<EventSource | null>(null)

  const [linkedinLogs, setLinkedinLogs] = useState('')
  const [competitorLogs, setCompetitorLogs] = useState('')
  const [csvLogs, setCsvLogs] = useState('')

  useEffect(() => {
    if (linkedinLogRef.current) {
      linkedinLogRef.current.scrollTop = linkedinLogRef.current.scrollHeight
    }
  }, [linkedinLogs])

  useEffect(() => {
    if (competitorLogRef.current) {
      competitorLogRef.current.scrollTop = competitorLogRef.current.scrollHeight
    }
  }, [competitorLogs])

  useEffect(() => {
    if (csvLogRef.current) {
      csvLogRef.current.scrollTop = csvLogRef.current.scrollHeight
    }
  }, [csvLogs])

  useEffect(() => {
    return () => {
      linkedinSourceRef.current?.close()
      competitorSourceRef.current?.close()
      csvSourceRef.current?.close()
    }
  }, [])

  async function handleStartLinkedin() {
    if (!linkedinKeyword.trim()) return
    try {
      setError(null)
      setLoading(true)
      setLinkedinResult(null)
      setLinkedinLogs('')
      setLinkedinRunId(null)
      setLinkedinPaused(false)
      linkedinSourceRef.current?.close()

      const url = `${FINDER_BASE_URL}/scrape/linkedin/stream?keyword=${encodeURIComponent(
        linkedinKeyword.trim(),
      )}`
      const es = new EventSource(url)
      linkedinSourceRef.current = es

      es.addEventListener('run_id', (event) => {
        const e = event as MessageEvent
        setLinkedinRunId(String(e.data))
      })

      es.addEventListener('log', (event) => {
        const e = event as MessageEvent
        setLinkedinLogs((prev) => (prev ? `${prev}\n${e.data}` : String(e.data)))
      })

      es.addEventListener('result', (event) => {
        const e = event as MessageEvent
        try {
          const data = JSON.parse(e.data) as ScrapeResult['result']
          setLinkedinResult({ status: 'SUCCESS', result: data, logs: null })
        } catch (err) {
          setError(err instanceof Error ? err.message : 'Failed to parse LinkedIn result')
        } finally {
          setLoading(false)
          es.close()
          linkedinSourceRef.current = null
        }
      })

      es.onerror = () => {
        setError('LinkedIn stream error')
        setLoading(false)
        es.close()
        linkedinSourceRef.current = null
      }
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Failed to run LinkedIn scrape')
      setLoading(false)
    }
  }

  async function handleStartCompetitors() {
    const brands = competitorBrands
      .split(',')
      .map((b) => b.trim())
      .filter(Boolean)
    if (!brands.length) return
    try {
      setError(null)
      setLoading(true)
      setCompetitorResult(null)
      setCompetitorLogs('')
      setCompetitorRunId(null)
      setCompetitorPaused(false)
      competitorSourceRef.current?.close()

      const url = `${FINDER_BASE_URL}/scrape/competitors/stream?brands=${encodeURIComponent(
        brands.join(','),
      )}`
      const es = new EventSource(url)
      competitorSourceRef.current = es

      es.addEventListener('run_id', (event) => {
        const e = event as MessageEvent
        setCompetitorRunId(String(e.data))
      })

      es.addEventListener('log', (event) => {
        const e = event as MessageEvent
        setCompetitorLogs((prev) => (prev ? `${prev}\n${e.data}` : String(e.data)))
      })

      es.addEventListener('result', (event) => {
        const e = event as MessageEvent
        try {
          const data = JSON.parse(e.data) as ScrapeResult['result']
          setCompetitorResult({ status: 'SUCCESS', result: data, logs: null })
        } catch (err) {
          setError(err instanceof Error ? err.message : 'Failed to parse competitor result')
        } finally {
          setLoading(false)
          es.close()
          competitorSourceRef.current = null
        }
      })

      es.onerror = () => {
        setError('Competitor stream error')
        setLoading(false)
        es.close()
        competitorSourceRef.current = null
      }
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Failed to run competitor scrape')
    } finally {
      setLoading(false)
    }
  }

  async function handleCsvFileChange(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0]
    if (!file) return

    try {
      setError(null)
      setLoading(true)

      const formData = new FormData()
      formData.append('file', file)

      const res = await fetch(`${FINDER_BASE_URL}/upload/shop-file`, {
        method: 'POST',
        body: formData,
      })

      if (!res.ok) {
        const text = await res.text()
        throw new Error(text || 'Failed to upload file')
      }

      const data = (await res.json()) as { file_path?: string; error?: string }
      if (!data.file_path) {
        throw new Error(data.error || 'Upload did not return a file path')
      }

      setCsvPath(data.file_path)
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to upload file'
      setError(message)
    } finally {
      setLoading(false)
    }
  }

  async function handleStartCsv() {
    if (!csvPath.trim()) return
    try {
      setError(null)
      setLoading(true)
      setCsvResult(null)
      setCsvLogs('')
      setCsvRunId(null)
      setCsvPaused(false)
      csvSourceRef.current?.close()

      const params = new URLSearchParams({
        file_path: csvPath.trim(),
        source: csvSource.trim() || 'csv_upload',
      })
      const url = `${FINDER_BASE_URL}/scrape/csv/stream?${params.toString()}`
      const es = new EventSource(url)
      csvSourceRef.current = es

      es.addEventListener('run_id', (event) => {
        const e = event as MessageEvent
        setCsvRunId(String(e.data))
      })

      es.addEventListener('log', (event) => {
        const e = event as MessageEvent
        setCsvLogs((prev) => (prev ? `${prev}\n${e.data}` : String(e.data)))
      })

      es.addEventListener('result', (event) => {
        const e = event as MessageEvent
        try {
          const data = JSON.parse(e.data) as ScrapeResult['result']
          setCsvResult({ status: 'SUCCESS', result: data, logs: null })
        } catch (err) {
          setError(err instanceof Error ? err.message : 'Failed to parse CSV result')
        } finally {
          setLoading(false)
          es.close()
          csvSourceRef.current = null
        }
      })

      es.onerror = () => {
        setError('CSV stream error')
        setLoading(false)
        es.close()
        csvSourceRef.current = null
      }
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Failed to run CSV scrape')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-1">
        <h1 className="text-2xl md:text-3xl font-semibold tracking-tight text-slate-50 pb-6">
          Scraping Console
        </h1>
        <p className="text-sm text-slate-400 max-w-xl">
          Orchestrate LinkedIn discovery, competitor analysis, and CSV/PDF processing from a single live console.
        </p>
      </div>
      <div className="rounded-2xl border border-white/10 bg-slate-900/70 shadow-[0_18px_40px_rgba(15,23,42,0.9)] backdrop-blur-2xl overflow-hidden">
        <div className="flex border-b border-white/10 bg-slate-900/80">
          <button
            className={`relative px-4 py-3 text-xs font-medium uppercase tracking-[0.16em] border-b-2 transition-colors ${
              activeTab === 'linkedin'
                ? 'border-emerald-400 text-emerald-300'
                : 'border-transparent text-slate-500 hover:text-slate-200'
            }`}
            onClick={() => setActiveTab('linkedin')}
          >
            LinkedIn Scraping
          </button>
          <button
            className={`relative px-4 py-3 text-xs font-medium uppercase tracking-[0.16em] border-b-2 transition-colors ${
              activeTab === 'competitors'
                ? 'border-emerald-400 text-emerald-300'
                : 'border-transparent text-slate-500 hover:text-slate-200'
            }`}
            onClick={() => setActiveTab('competitors')}
          >
            Competitor Discovery
          </button>
          <button
            className={`relative px-4 py-3 text-xs font-medium uppercase tracking-[0.16em] border-b-2 transition-colors ${
              activeTab === 'csv'
                ? 'border-emerald-400 text-emerald-300'
                : 'border-transparent text-slate-500 hover:text-slate-200'
            }`}
            onClick={() => setActiveTab('csv')}
          >
            CSV/PDF Processing
          </button>
        </div>

        <div className="p-5 space-y-6">
          {activeTab === 'linkedin' && (
            <div className="space-y-4">
              <div className="space-y-2">
                <h2 className="font-medium text-sm text-slate-100">LinkedIn Scraping</h2>
                <input
                  className="w-full rounded-md border border-slate-700/70 bg-slate-950/60 px-3 py-2 text-sm text-slate-100 placeholder:text-slate-500 focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-emerald-400/80 focus-visible:border-emerald-400/80"
                  placeholder="Keyword (e.g. retail buyer)"
                  value={linkedinKeyword}
                  onChange={(e) => setLinkedinKeyword(e.target.value)}
                />
                <button
                  className="inline-flex items-center rounded-md bg-gradient-to-r from-emerald-400 via-sky-400 to-indigo-400 px-3 py-1.5 text-xs font-medium text-slate-950 shadow-[0_12px_30px_rgba(15,23,42,0.9)] transition-all hover:brightness-110 disabled:cursor-not-allowed disabled:opacity-60"
                  onClick={handleStartLinkedin}
                  disabled={!linkedinKeyword.trim() || loading}
                >
                  Run LinkedIn Scrape
                </button>
                {linkedinSourceRef.current && linkedinRunId && (
                  <button
                    className="ml-2 inline-flex items-center rounded-md border border-slate-700/70 bg-slate-900/70 px-3 py-1 text-[0.7rem] font-medium text-slate-300 hover:border-emerald-400/50 hover:bg-slate-900/90"
                    type="button"
                    onClick={async () => {
                      try {
                        const endpoint = linkedinPaused ? 'resume' : 'pause'
                        await fetch(`${FINDER_BASE_URL}/scrape/linkedin/${endpoint}`, {
                          method: 'POST',
                          headers: { 'Content-Type': 'application/json' },
                          body: JSON.stringify({ run_id: linkedinRunId }),
                        })
                        setLinkedinPaused(!linkedinPaused)
                      } catch {
                        // ignore pause/resume errors in UI
                      }
                    }}
                  >
                    {linkedinPaused ? 'Continue' : 'Stop'}
                  </button>
                )}
                {linkedinSourceRef.current && (
                  <button
                    className="ml-2 px-3 py-1 text-xs rounded border text-muted-foreground hover:bg-accent"
                    type="button"
                    onClick={async () => {
                      try {
                        if (linkedinRunId) {
                          await fetch(`${FINDER_BASE_URL}/scrape/linkedin/cancel`, {
                            method: 'POST',
                            headers: { 'Content-Type': 'application/json' },
                            body: JSON.stringify({ run_id: linkedinRunId }),
                          })
                        }
                      } catch {
                        // ignore cancel errors in UI
                      } finally {
                        linkedinSourceRef.current?.close()
                        linkedinSourceRef.current = null
                        setLinkedinPaused(false)
                        setLoading(false)
                      }
                    }}
                  >
                    Cancel
                  </button>
                )}
                {linkedinResult && (
                  <button
                    className="ml-2 px-3 py-1 text-xs rounded border text-muted-foreground hover:bg-accent"
                    type="button"
                    onClick={() => {
                      setLinkedinResult(null)
                      setLinkedinLogs('')
                    }}
                  >
                    Clear
                  </button>
                )}
              </div>

              <div className="grid gap-4 md:grid-cols-1">
                <div className="space-y-2">
                  <h3 className="font-medium text-sm text-slate-100">Run Log</h3>
                  {linkedinLogs ? (
                    <pre
                      ref={linkedinLogRef}
                      className="mt-1 max-h-72 overflow-auto rounded-lg border border-slate-800/80 bg-black/90 p-3 text-[0.7rem] leading-snug font-mono text-emerald-300 shadow-inner"
                    >
                      {linkedinLogs}
                    </pre>
                  ) : (
                    <div className="text-xs text-slate-500">Logs will appear here after a run.</div>
                  )}
                </div>

                <div className="space-y-2">
                  <h3 className="font-medium text-sm text-slate-100">Result</h3>
                  {linkedinResult ? (
                    <pre className="mt-1 max-h-72 overflow-auto rounded-lg border border-slate-800/80 bg-slate-950/80 p-3 text-[0.7rem] text-slate-100">
                      {JSON.stringify(linkedinResult.result, null, 2)}
                    </pre>
                  ) : (
                    <div className="text-xs text-slate-500">No LinkedIn scrape run yet.</div>
                  )}
                </div>
              </div>
            </div>
          )}

          {activeTab === 'competitors' && (
            <div className="space-y-4">
              <div className="space-y-2">
                <h2 className="font-medium text-sm text-slate-100">Competitor Discovery</h2>
                <input
                  className="w-full rounded-md border border-slate-700/70 bg-slate-950/60 px-3 py-2 text-sm text-slate-100 placeholder:text-slate-500 focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-emerald-400/80 focus-visible:border-emerald-400/80"
                  placeholder="Brands (comma separated)"
                  value={competitorBrands}
                  onChange={(e) => setCompetitorBrands(e.target.value)}
                />
                <button
                  className="inline-flex items-center rounded-md bg-gradient-to-r from-emerald-400 via-sky-400 to-indigo-400 px-3 py-1.5 text-xs font-medium text-slate-950 shadow-[0_12px_30px_rgba(15,23,42,0.9)] transition-all hover:brightness-110 disabled:cursor-not-allowed disabled:opacity-60"
                  onClick={handleStartCompetitors}
                  disabled={!competitorBrands.trim() || loading}
                >
                  Run Competitor Scrape
                </button>
                {competitorSourceRef.current && competitorRunId && (
                  <button
                    className="ml-2 px-3 py-1 text-xs rounded border text-muted-foreground hover:bg-accent"
                    type="button"
                    onClick={async () => {
                      try {
                        const endpoint = competitorPaused ? 'resume' : 'pause'
                        await fetch(`${FINDER_BASE_URL}/scrape/competitors/${endpoint}`, {
                          method: 'POST',
                          headers: { 'Content-Type': 'application/json' },
                          body: JSON.stringify({ run_id: competitorRunId }),
                        })
                        setCompetitorPaused(!competitorPaused)
                      } catch {
                        // ignore pause/resume errors in UI
                      }
                    }}
                  >
                    {competitorPaused ? 'Continue' : 'Stop'}
                  </button>
                )}
                {competitorSourceRef.current && (
                  <button
                    className="ml-2 px-3 py-1 text-xs rounded border text-muted-foreground hover:bg-accent"
                    type="button"
                    onClick={async () => {
                      try {
                        if (competitorRunId) {
                          await fetch(`${FINDER_BASE_URL}/scrape/competitors/cancel`, {
                            method: 'POST',
                            headers: { 'Content-Type': 'application/json' },
                            body: JSON.stringify({ run_id: competitorRunId }),
                          })
                        }
                      } catch {
                        // ignore cancel errors in UI
                      } finally {
                        competitorSourceRef.current?.close()
                        competitorSourceRef.current = null
                        setCompetitorPaused(false)
                        setLoading(false)
                      }
                    }}
                  >
                    Cancel
                  </button>
                )}
                {competitorResult && (
                  <button
                    className="ml-2 px-3 py-1 text-xs rounded border text-muted-foreground hover:bg-accent"
                    type="button"
                    onClick={() => {
                      setCompetitorResult(null)
                      setCompetitorLogs('')
                    }}
                  >
                    Clear
                  </button>
                )}
              </div>

              <div className="grid gap-4 md:grid-cols-1">
                <div className="space-y-2">
                  <h3 className="font-medium text-sm">Run Log</h3>
                  {competitorLogs ? (
                    <pre
                      ref={competitorLogRef}
                      className="mt-1 max-h-72 overflow-auto rounded-lg border border-slate-800/80 bg-black/90 p-3 text-[0.7rem] leading-snug font-mono text-emerald-300 shadow-inner"
                    >
                      {competitorLogs}
                    </pre>
                  ) : (
                    <div className="text-sm text-gray-500">Logs will appear here after a run.</div>
                  )}
                </div>

                <div className="space-y-2">
                  <h3 className="font-medium text-sm">Result</h3>
                  {competitorResult ? (
                    <pre className="mt-1 max-h-72 overflow-auto bg-gray-50 border rounded p-2 text-xs">
                      {JSON.stringify(competitorResult.result, null, 2)}
                    </pre>
                  ) : (
                    <div className="text-xs text-slate-500">No competitor scrape run yet.</div>
                  )}
                </div>
              </div>
            </div>
          )}

          {activeTab === 'csv' && (
            <div className="space-y-4">
              <div className="space-y-2">
                <h2 className="font-medium text-sm text-slate-100">CSV/PDF Processing</h2>
                <input
                  type="file"
                  accept=".pdf,.csv,.json"
                  className="w-full rounded-md border border-slate-700/70 bg-slate-950/60 px-3 py-2 text-sm text-slate-100 file:mr-3 file:rounded-md file:border-0 file:bg-slate-800 file:px-3 file:py-1 file:text-xs file:font-medium file:text-slate-100 hover:file:bg-slate-700/80 focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-emerald-400/80 focus-visible:border-emerald-400/80"
                  onChange={handleCsvFileChange}
                  disabled={loading}
                />
                {csvPath && (
                  <div className="text-[0.7rem] text-slate-400 break-all">
                    Uploaded to server as:
                    <br />
                    <code>{csvPath}</code>
                  </div>
                )}
                <button
                  className="inline-flex items-center rounded-md bg-gradient-to-r from-emerald-400 via-sky-400 to-indigo-400 px-3 py-1.5 text-xs font-medium text-slate-950 shadow-[0_12px_30px_rgba(15,23,42,0.9)] transition-all hover:brightness-110 disabled:cursor-not-allowed disabled:opacity-60"
                  onClick={handleStartCsv}
                  disabled={!csvPath.trim() || loading}
                >
                  Run CSV Scrape
                </button>
                {csvSourceRef.current && csvRunId && (
                  <button
                    className="ml-2 px-3 py-1 text-xs rounded border text-muted-foreground hover:bg-accent"
                    type="button"
                    onClick={async () => {
                      try {
                        const endpoint = csvPaused ? 'resume' : 'pause'
                        await fetch(`${FINDER_BASE_URL}/scrape/csv/${endpoint}`, {
                          method: 'POST',
                          headers: { 'Content-Type': 'application/json' },
                          body: JSON.stringify({ run_id: csvRunId }),
                        })
                        setCsvPaused(!csvPaused)
                      } catch {
                        // ignore pause/resume errors in UI
                      }
                    }}
                  >
                    {csvPaused ? 'Continue' : 'Stop'}
                  </button>
                )}
                {csvSourceRef.current && (
                  <button
                    className="ml-2 px-3 py-1 text-xs rounded border text-muted-foreground hover:bg-accent"
                    type="button"
                    onClick={async () => {
                      try {
                        if (csvRunId) {
                          await fetch(`${FINDER_BASE_URL}/scrape/csv/cancel`, {
                            method: 'POST',
                            headers: { 'Content-Type': 'application/json' },
                            body: JSON.stringify({ run_id: csvRunId }),
                          })
                        }
                      } catch {
                        // ignore cancel errors in UI
                      } finally {
                        csvSourceRef.current?.close()
                        csvSourceRef.current = null
                        setCsvPaused(false)
                        setLoading(false)
                      }
                    }}
                  >
                    Cancel
                  </button>
                )}
                {csvResult && (
                  <button
                    className="ml-2 px-3 py-1 text-xs rounded border text-muted-foreground hover:bg-accent"
                    type="button"
                    onClick={() => {
                      setCsvResult(null)
                      setCsvLogs('')
                    }}
                  >
                    Clear
                  </button>
                )}
              </div>

              <div className="grid gap-4 md:grid-cols-1">
                <div className="space-y-2">
                  <h3 className="font-medium text-sm">Run Log</h3>
                  {csvLogs ? (
                    <pre
                      ref={csvLogRef}
                      className="mt-1 max-h-72 overflow-auto rounded-lg border border-slate-800/80 bg-black/90 p-3 text-[0.7rem] leading-snug font-mono text-emerald-300 shadow-inner"
                    >
                      {csvLogs}
                    </pre>
                  ) : (
                    <div className="text-sm text-gray-500">Logs will appear here after a run.</div>
                  )}
                </div>
                
                <div className="space-y-2">
                  <h3 className="font-medium text-sm">Result</h3>
                  {csvResult ? (
                    <pre className="mt-1 max-h-72 overflow-auto bg-gray-50 border rounded p-2 text-xs">
                      {JSON.stringify(csvResult.result, null, 2)}
                    </pre>
                  ) : (
                    <div className="text-xs text-slate-500">No CSV scrape run yet.</div>
                  )}
                </div>
              </div>
            </div>
          )}
        </div>
      </div>

      {error && (
        <div className="mt-4 rounded-xl border border-red-500/40 bg-red-500/10 p-3 text-xs text-red-100 shadow-[0_10px_30px_rgba(127,29,29,0.5)]">
          {error}
        </div>
      )}

    </div>
  )
}

export default ScrapingConsole
