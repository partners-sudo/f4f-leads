const FINDER_BASE_URL = import.meta.env.VITE_FINDER_BASE_URL ?? 'http://localhost:8001'

export interface ScrapeResult {
  status: string
  result: Record<string, unknown>
  logs?: string | null
}

export const finderApi = {
  async runLinkedinScrape(keyword: string): Promise<ScrapeResult> {
    const res = await fetch(`${FINDER_BASE_URL}/scrape/linkedin`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ keyword }),
    })
    if (!res.ok) {
      throw new Error(`Finder API error: ${res.statusText}`)
    }
    return res.json()
  },

  async runCompetitorScrape(brands: string[]): Promise<ScrapeResult> {
    const res = await fetch(`${FINDER_BASE_URL}/scrape/competitors`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ brands }),
    })
    if (!res.ok) {
      throw new Error(`Finder API error: ${res.statusText}`)
    }
    return res.json()
  },

  async runCsvScrape(filePath: string, source: string): Promise<ScrapeResult> {
    const res = await fetch(`${FINDER_BASE_URL}/scrape/csv`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ file_path: filePath, source }),
    })
    if (!res.ok) {
      throw new Error(`Finder API error: ${res.statusText}`)
    }
    return res.json()
  },
}
