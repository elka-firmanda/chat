import { X } from 'lucide-react'

export default function SettingsModal() {
  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center p-4">
      <div className="bg-background rounded-xl w-full max-w-2xl max-h-[80vh] overflow-auto">
        <div className="flex items-center justify-between p-4 border-b">
          <h2 className="text-xl font-semibold">Settings</h2>
          <button className="p-2 hover:bg-accent rounded-lg">
            <X size={18} />
          </button>
        </div>
        <div className="p-4">
          <p className="text-muted-foreground">Settings interface coming soon...</p>
        </div>
      </div>
    </div>
  )
}
