import { useEffect, useRef, useState } from 'react'
import type { ScrapeResult } from '@/lib/finder'
import { FINDER_BASE_URL, finderApi } from '@/lib/finder'

function ScrapingConsole() {
  const [linkedinKeyword, setLinkedinKeyword] = useState('retail buyer')
  const [competitorBrands, setCompetitorBrands] = useState('Funko, Tubbz, Cable guys')
  const [csvPath, setCsvPath] = useState('')
  const [csvSource, setCsvSource] = useState('csv_upload')

  const [activeTab, setActiveTab] = useState<'linkedin' | 'competitors' | 'csv'>('linkedin')

  const [linkedinResult, setLinkedinResult] = useState<ScrapeResult | null>(null)
  const [competitorResult, setCompetitorResult] = useState<ScrapeResult | null>(null)
  const [csvResult, setCsvResult] = useState<ScrapeResult | null>(null)
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
      linkedinSourceRef.current?.close()

      const url = `${FINDER_BASE_URL}/scrape/linkedin/stream?keyword=${encodeURIComponent(
        linkedinKeyword.trim(),
      )}`
      const es = new EventSource(url)
      linkedinSourceRef.current = es

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
      competitorSourceRef.current?.close()

      const url = `${FINDER_BASE_URL}/scrape/competitors/stream?brands=${encodeURIComponent(
        brands.join(','),
      )}`
      const es = new EventSource(url)
      competitorSourceRef.current = es

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

  async function handleStartCsv() {
    if (!csvPath.trim()) return
    try {
      setError(null)
      setLoading(true)
      setCsvResult(null)
      setCsvLogs('')
      csvSourceRef.current?.close()

      const params = new URLSearchParams({
        file_path: csvPath.trim(),
        source: csvSource.trim() || 'csv_upload',
      })
      const url = `${FINDER_BASE_URL}/scrape/csv/stream?${params.toString()}`
      const es = new EventSource(url)
      csvSourceRef.current = es

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
    <div className="p-6 space-y-8">
      <h1 className="text-2xl font-semibold mb-4">Scraping Console</h1>
      <div className="border rounded-lg bg-card">
        <div className="flex border-b">
          <button
            className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors ${
              activeTab === 'linkedin'
                ? 'border-blue-600 text-blue-600'
                : 'border-transparent text-muted-foreground hover:text-foreground'
            }`}
            onClick={() => setActiveTab('linkedin')}
          >
            LinkedIn Scraping
          </button>
          <button
            className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors ${
              activeTab === 'competitors'
                ? 'border-blue-600 text-blue-600'
                : 'border-transparent text-muted-foreground hover:text-foreground'
            }`}
            onClick={() => setActiveTab('competitors')}
          >
            Competitor Discovery
          </button>
          <button
            className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors ${
              activeTab === 'csv'
                ? 'border-blue-600 text-blue-600'
                : 'border-transparent text-muted-foreground hover:text-foreground'
            }`}
            onClick={() => setActiveTab('csv')}
          >
            CSV/PDF Processing
          </button>
        </div>

        <div className="p-4 space-y-4">
          {activeTab === 'linkedin' && (
            <div className="space-y-4">
              <div className="space-y-2">
                <h2 className="font-medium text-sm">LinkedIn Scraping</h2>
                <input
                  className="w-full border rounded px-2 py-1 text-sm"
                  placeholder="Keyword (e.g. retail buyer)"
                  value={linkedinKeyword}
                  onChange={(e) => setLinkedinKeyword(e.target.value)}
                  disabled={true}
                />
                <button
                  className="px-3 py-1 text-sm rounded bg-blue-600 text-white disabled:opacity-50"
                  onClick={handleStartLinkedin}
                  disabled={!linkedinKeyword.trim() || loading}
                >
                  Run LinkedIn Scrape
                </button>
                {linkedinSourceRef.current && (
                  <button
                    className="ml-2 px-3 py-1 text-xs rounded border text-muted-foreground hover:bg-accent"
                    type="button"
                    onClick={() => {
                      linkedinSourceRef.current?.close()
                      linkedinSourceRef.current = null
                      setLoading(false)
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
                  <h3 className="font-medium text-sm">Run Log</h3>
                  {linkedinLogs ? (
                    <pre
                      ref={linkedinLogRef}
                      className="mt-1 max-h-72 overflow-auto bg-black text-green-200 border rounded p-2 text-xs leading-snug font-mono"
                    >
                      {linkedinLogs}
                    </pre>
                  ) : (
                    <div className="text-sm text-gray-500">Logs will appear here after a run.</div>
                  )}
                </div>

                <div className="space-y-2">
                  <h3 className="font-medium text-sm">Result</h3>
                  {linkedinResult ? (
                    <pre className="mt-1 max-h-72 overflow-auto bg-gray-50 border rounded p-2 text-xs">
                      {JSON.stringify(linkedinResult.result, null, 2)}
                    </pre>
                  ) : (
                    <div className="text-sm text-gray-500">No LinkedIn scrape run yet.</div>
                  )}
                </div>
              </div>
            </div>
          )}

          {activeTab === 'competitors' && (
            <div className="space-y-4">
              <div className="space-y-2">
                <h2 className="font-medium text-sm">Competitor Discovery</h2>
                <input
                  className="w-full border rounded px-2 py-1 text-sm"
                  placeholder="Brands (comma separated)"
                  value={competitorBrands}
                  onChange={(e) => setCompetitorBrands(e.target.value)}
                  disabled={true}
                />
                <button
                  className="px-3 py-1 text-sm rounded bg-blue-600 text-white disabled:opacity-50"
                  onClick={handleStartCompetitors}
                  disabled={!competitorBrands.trim() || loading}
                >
                  Run Competitor Scrape
                </button>
                {competitorSourceRef.current && (
                  <button
                    className="ml-2 px-3 py-1 text-xs rounded border text-muted-foreground hover:bg-accent"
                    type="button"
                    onClick={() => {
                      competitorSourceRef.current?.close()
                      competitorSourceRef.current = null
                      setLoading(false)
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
                      className="mt-1 max-h-72 overflow-auto bg-black text-green-200 border rounded p-2 text-xs leading-snug font-mono"
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
                    <div className="text-sm text-gray-500">No competitor scrape run yet.</div>
                  )}
                </div>
              </div>
            </div>
          )}

          {activeTab === 'csv' && (
            <div className="space-y-4">
              <div className="space-y-2">
                <h2 className="font-medium text-sm">CSV/PDF Processing</h2>
                <input
                  className="w-full border rounded px-2 py-1 text-sm"
                  placeholder="File path on server"
                  value={csvPath}
                  onChange={(e) => setCsvPath(e.target.value)}
                />
                <input
                  className="w-full border rounded px-2 py-1 text-sm"
                  placeholder="Source tag (e.g. csv_upload)"
                  value={csvSource}
                  onChange={(e) => setCsvSource(e.target.value)}
                  disabled={true}
                />
                <button
                  className="px-3 py-1 text-sm rounded bg-blue-600 text-white disabled:opacity-50"
                  onClick={handleStartCsv}
                  disabled={!csvPath.trim() || loading}
                >
                  Run CSV Scrape
                </button>
                {csvSourceRef.current && (
                  <button
                    className="ml-2 px-3 py-1 text-xs rounded border text-muted-foreground hover:bg-accent"
                    type="button"
                    onClick={() => {
                      csvSourceRef.current?.close()
                      csvSourceRef.current = null
                      setLoading(false)
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
                      className="mt-1 max-h-72 overflow-auto bg-black text-green-200 border rounded p-2 text-xs leading-snug font-mono"
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
                    <div className="text-sm text-gray-500">No CSV scrape run yet.</div>
                  )}
                </div>
              </div>
            </div>
          )}
        </div>
      </div>

      {error && (
        <div className="border rounded-lg p-3 text-sm text-red-600 bg-red-50">{error}</div>
      )}

    </div>
  )
}

export default ScrapingConsole
