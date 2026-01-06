import { Download } from 'lucide-react'

interface Chart {
  filename: string
  data: string
}

interface ChartDisplayProps {
  charts: Chart[]
}

export default function ChartDisplay({ charts }: ChartDisplayProps) {
  if (!charts || charts.length === 0) return null

  const handleDownload = (filename: string, data: string) => {
    const link = document.createElement('a')
    link.href = `data:image/png;base64,${data}`
    link.download = filename
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
  }

  return (
    <div className={`grid gap-4 mt-4 w-full ${charts.length > 1 ? 'grid-cols-1 md:grid-cols-2' : 'grid-cols-1'}`}>
      {charts.map((chart, index) => (
        <div
          key={index}
          className="relative group bg-card border border-border rounded-xl overflow-hidden shadow-sm hover:shadow-md transition-all duration-200"
        >
          {/* Chart Image Container - White background to ensure chart readability in dark mode */}
          <div className="aspect-[4/3] w-full bg-white flex items-center justify-center p-2">
            <img
              src={`data:image/png;base64,${chart.data}`}
              alt={chart.filename}
              className="max-w-full max-h-full object-contain"
            />
          </div>

          {/* Download Overlay */}
          <div className="absolute top-2 right-2 opacity-0 group-hover:opacity-100 transition-opacity duration-200">
            <button
              onClick={(e) => {
                e.stopPropagation()
                handleDownload(chart.filename, chart.data)
              }}
              className="p-2 bg-white/90 shadow-sm border border-slate-200 rounded-lg hover:bg-white text-slate-700 transition-colors"
              title={`Download ${chart.filename}`}
            >
              <Download className="w-4 h-4" />
            </button>
          </div>

          {/* Caption/Footer */}
          <div className="px-3 py-2 border-t border-border bg-secondary/30">
            <p className="text-xs font-medium text-muted-foreground truncate" title={chart.filename}>
              {chart.filename}
            </p>
          </div>
        </div>
      ))}
    </div>
  )
}
