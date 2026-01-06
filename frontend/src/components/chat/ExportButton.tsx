import { useState } from 'react'
import { Download, FileText, FileSpreadsheet, FileJson, ChevronDown } from 'lucide-react'

interface ExportButtonProps {
  sessionId: string
  className?: string
}

type ExportFormat = 'pdf' | 'csv' | 'json'

export default function ExportButton({ sessionId, className }: ExportButtonProps) {
  const [isOpen, setIsOpen] = useState(false)
  const [isExporting, setIsExporting] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const handleExport = async (format: ExportFormat) => {
    setIsOpen(false)
    setIsExporting(true)
    setError(null)

    try {
      // TODO: Implement export API calls
      // This is a placeholder that will be implemented when the export API is ready
      console.log(`Exporting session ${sessionId} as ${format}`)
      
      // Simulate API call
      await new Promise(resolve => setTimeout(resolve, 1000))
      
      // When the API is ready, use this pattern:
      // const exportDoc = await api.createComparisonExport(sessionId)
      // const blob = await api.downloadComparisonPDF/CSV/JSON(exportDoc.id)
      // const filename = `${exportDoc.title.replace(/ /g, '_')}.${format}`
      // Download blob...
      
    } catch (err) {
      console.error('Export failed:', err)
      setError(err instanceof Error ? err.message : 'Export failed')
    } finally {
      setIsExporting(false)
    }
  }

  return (
    <div className={`relative ${className || ''}`}>
      <button
        onClick={() => setIsOpen(!isOpen)}
        disabled={isExporting}
        className={`
          flex items-center gap-2 px-3 py-2 text-sm font-medium rounded-lg
          border border-border bg-card hover:bg-secondary
          transition-colors duration-200
          disabled:opacity-50 disabled:cursor-not-allowed
          focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2
        `}
        title="Export comparison report"
      >
        <Download className="w-4 h-4" />
        {isExporting ? 'Exporting...' : 'Export Report'}
        {!isExporting && <ChevronDown className="w-3 h-3 ml-1" />}
      </button>

      {/* Dropdown menu */}
      {isOpen && !isExporting && (
        <>
          {/* Backdrop */}
          <div
            className="fixed inset-0 z-10"
            onClick={() => setIsOpen(false)}
          />

          {/* Menu */}
          <div className="absolute right-0 mt-2 w-48 bg-card border border-border rounded-lg shadow-lg z-20 overflow-hidden">
            <div className="py-1">
              <button
                onClick={() => handleExport('pdf')}
                className="w-full flex items-center gap-3 px-4 py-2.5 text-sm hover:bg-secondary transition-colors text-left"
              >
                <FileText className="w-4 h-4 text-muted-foreground" />
                <div>
                  <div className="font-medium">PDF</div>
                  <div className="text-xs text-muted-foreground">
                    Formatted report with charts
                  </div>
                </div>
              </button>

              <button
                onClick={() => handleExport('csv')}
                className="w-full flex items-center gap-3 px-4 py-2.5 text-sm hover:bg-secondary transition-colors text-left"
              >
                <FileSpreadsheet className="w-4 h-4 text-muted-foreground" />
                <div>
                  <div className="font-medium">CSV</div>
                  <div className="text-xs text-muted-foreground">
                    Tabular data for spreadsheets
                  </div>
                </div>
              </button>

              <button
                onClick={() => handleExport('json')}
                className="w-full flex items-center gap-3 px-4 py-2.5 text-sm hover:bg-secondary transition-colors text-left"
              >
                <FileJson className="w-4 h-4 text-muted-foreground" />
                <div>
                  <div className="font-medium">JSON</div>
                  <div className="text-xs text-muted-foreground">
                    Raw structured data
                  </div>
                </div>
              </button>
            </div>
          </div>
        </>
      )}

      {/* Error message */}
      {error && (
        <div className="absolute right-0 mt-2 px-3 py-2 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-900 rounded-lg text-sm text-red-700 dark:text-red-400 z-20">
          {error}
        </div>
      )}
    </div>
  )
}
