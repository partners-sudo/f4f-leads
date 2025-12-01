import { useState } from 'react'
import type { ScrapeResult } from '@/lib/finder'
import { finderApi } from '@/lib/finder'

function ScrapingConsole() {
  const [linkedinKeyword, setLinkedinKeyword] = useState('')
  const [competitorBrands, setCompetitorBrands] = useState('Funko, Tubbz, Cable guys')
  const [csvPath, setCsvPath] = useState('')
  const [csvSource, setCsvSource] = useState('csv_upload')

  const [linkedinResult, setLinkedinResult] = useState<ScrapeResult | null>(null)
  const [competitorResult, setCompetitorResult] = useState<ScrapeResult | null>(null)
  const [csvResult, setCsvResult] = useState<ScrapeResult | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function handleStartLinkedin() {
    if (!linkedinKeyword.trim()) return
    try {
      setError(null)
      setLoading(true)
      const result = await finderApi.runLinkedinScrape(linkedinKeyword.trim())
      setLinkedinResult(result)
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Failed to run LinkedIn scrape')
    } finally {
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
      const result = await finderApi.runCompetitorScrape(brands)
      setCompetitorResult(result)
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
      const result = await finderApi.runCsvScrape(csvPath.trim(), csvSource.trim() || 'csv_upload')
      setCsvResult(result)
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Failed to run CSV scrape')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="p-6 space-y-8">
      <h1 className="text-2xl font-semibold mb-4">Scraping Console</h1>

      <div className="grid gap-6 md:grid-cols-3">
        <div className="border rounded-lg p-4 space-y-3">
          <h2 className="font-medium">LinkedIn Scraping</h2>
          <input
            className="w-full border rounded px-2 py-1 text-sm"
            placeholder="Keyword (e.g. retail buyer)"
            value={linkedinKeyword}
            onChange={(e) => setLinkedinKeyword(e.target.value)}
          />
          <button
            className="px-3 py-1 text-sm rounded bg-blue-600 text-white disabled:opacity-50"
            onClick={handleStartLinkedin}
            disabled={!linkedinKeyword.trim() || loading}
          >
            Start LinkedIn Job
          </button>
        </div>

        <div className="border rounded-lg p-4 space-y-3">
          <h2 className="font-medium">Competitor Discovery</h2>
          <input
            className="w-full border rounded px-2 py-1 text-sm"
            placeholder="Brands (comma separated)"
            value={competitorBrands}
            onChange={(e) => setCompetitorBrands(e.target.value)}
          />
          <button
            className="px-3 py-1 text-sm rounded bg-blue-600 text-white disabled:opacity-50"
            onClick={handleStartCompetitors}
            disabled={!competitorBrands.trim() || loading}
          >
            Start Competitor Job
          </button>
        </div>

        <div className="border rounded-lg p-4 space-y-3">
          <h2 className="font-medium">CSV/PDF Processing</h2>
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
          />
          <button
            className="px-3 py-1 text-sm rounded bg-blue-600 text-white disabled:opacity-50"
            onClick={handleStartCsv}
            disabled={!csvPath.trim() || loading}
          >
            Start CSV Job
          </button>
        </div>
      </div>

      {error && (
        <div className="border rounded-lg p-3 text-sm text-red-600 bg-red-50">{error}</div>
      )}

      <div className="grid gap-6 md:grid-cols-3">
        <div className="border rounded-lg p-4 space-y-2">
          <h2 className="font-medium mb-2">LinkedIn Result</h2>
          {linkedinResult ? (
            <>
              <pre className="mt-2 max-h-64 overflow-auto bg-gray-50 border rounded p-2 text-xs">
                {JSON.stringify(linkedinResult.result, null, 2)}
              </pre>
              {linkedinResult.logs && (
                <pre className="mt-2 max-h-64 overflow-auto bg-black text-green-200 border rounded p-2 text-xs">
                  {linkedinResult.logs}
                </pre>
              )}
            </>
          ) : (
            <div className="text-sm text-gray-500">No LinkedIn scrape run yet.</div>
          )}
        </div>

        <div className="border rounded-lg p-4 space-y-2">
          <h2 className="font-medium mb-2">Competitor Result</h2>
          {competitorResult ? (
            <>
              <pre className="mt-2 max-h-64 overflow-auto bg-gray-50 border rounded p-2 text-xs">
                {JSON.stringify(competitorResult.result, null, 2)}
              </pre>
              {competitorResult.logs && (
                <pre className="mt-2 max-h-64 overflow-auto bg-black text-green-200 border rounded p-2 text-xs">
                  {competitorResult.logs}
                </pre>
              )}
            </>
          ) : (
            <div className="text-sm text-gray-500">No competitor scrape run yet.</div>
          )}
        </div>

        <div className="border rounded-lg p-4 space-y-2">
          <h2 className="font-medium mb-2">CSV Result</h2>
          {csvResult ? (
            <>
              <pre className="mt-2 max-h-64 overflow-auto bg-gray-50 border rounded p-2 text-xs">
                {JSON.stringify(csvResult.result, null, 2)}
              </pre>
              {csvResult.logs && (
                <pre className="mt-2 max-h-64 overflow-auto bg-black text-green-200 border rounded p-2 text-xs">
                  {csvResult.logs}
                </pre>
              )}
            </>
          ) : (
            <div className="text-sm text-gray-500">No CSV scrape run yet.</div>
          )}
        </div>
      </div>
    </div>
  )
}

export default ScrapingConsole
