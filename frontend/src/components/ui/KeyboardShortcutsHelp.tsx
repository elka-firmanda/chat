import { Keyboard } from 'lucide-react'

interface Shortcut {
  key: string
  description: string
}

interface KeyboardShortcutsHelpProps {
  isOpen: boolean
  onClose: () => void
}

const shortcuts: Shortcut[] = [
  { key: '⌘ + N', description: 'New chat' },
  { key: 'Ctrl + N', description: 'New chat (Windows)' },
  { key: '⌘ + Shift + ?', description: 'Show keyboard shortcuts' },
  { key: 'Ctrl + Shift + ?', description: 'Show shortcuts (Windows)' },
  { key: '⌘ + /', description: 'Toggle deep search' },
  { key: 'Ctrl + /', description: 'Toggle deep search (Windows)' },
  { key: '⌘ + ,', description: 'Open settings' },
  { key: 'Ctrl + ,', description: 'Open settings (Windows)' },
  { key: 'Escape', description: 'Go to home' },
]

export function KeyboardShortcutsHelp({ isOpen, onClose }: KeyboardShortcutsHelpProps) {
  if (!isOpen) return null

  return (
    <div className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-50 animate-in fade-in">
      <div className="bg-background rounded-xl w-full max-w-md mx-4 animate-in zoom-in-95">
        <div className="flex items-center justify-between p-4 border-b">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-primary/10 rounded-lg">
              <Keyboard size={20} className="text-primary" />
            </div>
            <div>
              <h2 className="font-semibold">Keyboard Shortcuts</h2>
              <p className="text-sm text-muted-foreground">Quick actions for faster workflow</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="min-h-[44px] min-w-[44px] flex items-center justify-center hover:bg-muted rounded-lg transition-colors"
          >
            ×
          </button>
        </div>

        <div className="p-4 space-y-2">
          {shortcuts.map((shortcut) => (
            <div
              key={shortcut.key}
              className="flex items-center justify-between py-2 px-3 rounded-lg hover:bg-muted/50"
            >
              <span className="text-sm text-muted-foreground">{shortcut.description}</span>
              <kbd className="px-2 py-1 bg-muted rounded text-xs font-mono">
                {shortcut.key}
              </kbd>
            </div>
          ))}
        </div>

        <div className="p-4 border-t bg-muted/30">
          <p className="text-xs text-center text-muted-foreground">
            Shortcuts don't work while typing in input fields
          </p>
        </div>
      </div>
    </div>
  )
}

export default KeyboardShortcutsHelp
