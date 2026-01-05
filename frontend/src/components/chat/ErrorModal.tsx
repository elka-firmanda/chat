import {
  AlertTriangle,
  RefreshCw,
  SkipForward,
  XCircle,
  Clock,
  ChevronDown,
  ChevronRight,
  Info,
  Settings,
  Wifi,
  Lock,
  Search,
} from 'lucide-react'
import * as Dialog from '@radix-ui/react-dialog'
import { useState, useEffect } from 'react'
import {
  getUserFriendlyError,
  createTechnicalDetails,
  logErrorToConsole,
  getSuggestedActions,
  type UserFriendlyError,
} from '../../utils/userFriendlyErrors'

interface ErrorDetails {
  error_type: string
  message: string
  timestamp: string
  retry_count: number
  max_retries: number
  can_retry: boolean
  step_info?: {
    type: string
    description: string
    step_number: number
  }
  context?: Record<string, unknown>
}

interface ErrorModalProps {
  isOpen: boolean
  onClose: () => void
  error: ErrorDetails | null
  interventionOptions: {
    retry: boolean
    skip: boolean
    abort: boolean
  }
  onRetry: () => void
  onSkip: () => void
  onAbort: () => void
  isLoading?: boolean
}

const getIconComponent = (iconName: string) => {
  const icons: Record<string, React.ReactNode> = {
    clock: <Clock className="w-5 h-5" />,
    alert: <AlertTriangle className="w-5 h-5" />,
    lock: <Lock className="w-5 h-5" />,
    wifi: <Wifi className="w-5 h-5" />,
    search: <Search className="w-5 h-5" />,
    info: <Info className="w-5 h-5" />,
  }
  return icons[iconName] || <AlertTriangle className="w-5 h-5" />
}

const getSeverityColor = (severity: 'info' | 'warning' | 'error') => {
  switch (severity) {
    case 'info':
      return 'bg-blue-100 dark:bg-blue-900/30 text-blue-600 dark:text-blue-400 border-blue-200 dark:border-blue-800'
    case 'warning':
      return 'bg-amber-100 dark:bg-amber-900/30 text-amber-600 dark:text-amber-400 border-amber-200 dark:border-amber-800'
    case 'error':
      return 'bg-red-100 dark:bg-red-900/30 text-red-600 dark:text-red-400 border-red-200 dark:border-red-800'
    default:
      return 'bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-400 border-gray-200 dark:border-gray-600'
  }
}

const getSeverityBgColor = (severity: 'info' | 'warning' | 'error') => {
  switch (severity) {
    case 'info':
      return 'bg-blue-50 dark:bg-blue-900/10'
    case 'warning':
      return 'bg-amber-50 dark:bg-amber-900/10'
    case 'error':
      return 'bg-red-50 dark:bg-red-900/10'
    default:
      return 'bg-gray-50 dark:bg-gray-800'
  }
}

export default function ErrorModal({
  isOpen,
  onClose,
  error,
  interventionOptions,
  onRetry,
  onSkip,
  onAbort,
  isLoading = false,
}: ErrorModalProps) {
  const [countdown, setCountdown] = useState(60)
  const [actionTaken, setActionTaken] = useState<string | null>(null)
  const [showTechnicalDetails, setShowTechnicalDetails] = useState(false)

  const friendlyError: UserFriendlyError | null = error
    ? getUserFriendlyError(error.error_type, error.message, error.context)
    : null

  const suggestedActions = error ? getSuggestedActions(error.error_type) : []

  const technicalDetails = error
    ? createTechnicalDetails(
        error.error_type,
        error.message,
        error.timestamp,
        error.retry_count,
        error.max_retries,
        error.context
      )
    : null

  useEffect(() => {
    if (isOpen && technicalDetails) {
      logErrorToConsole(technicalDetails)
    }
  }, [isOpen, technicalDetails])

  useEffect(() => {
    if (!isOpen || actionTaken) return

    const timer = setInterval(() => {
      setCountdown((prev) => {
        if (prev <= 1) {
          onAbort()
          return 0
        }
        return prev - 1
      })
    }, 1000)

    return () => clearInterval(timer)
  }, [isOpen, actionTaken, onAbort])

  const handleRetry = () => {
    setActionTaken('retry')
    onRetry()
  }

  const handleSkip = () => {
    setActionTaken('skip')
    onSkip()
  }

  const handleAbort = () => {
    setActionTaken('abort')
    onAbort()
  }

  if (!error || !friendlyError) return null

  return (
    <Dialog.Root open={isOpen} onOpenChange={(open) => !open && onClose()}>
      <Dialog.Portal>
        <Dialog.Overlay className="fixed inset-0 bg-black/50 backdrop-blur-sm z-50" />
        <Dialog.Content className="fixed left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 bg-white dark:bg-gray-800 rounded-xl shadow-2xl max-w-lg w-full mx-4 p-6 z-50 animate-in fade-in zoom-in-95 duration-200 max-h-[90vh] overflow-y-auto">
          <Dialog.Title className="sr-only">Error Dialog</Dialog.Title>
          <Dialog.Description className="sr-only">
            An error occurred during execution with user-friendly explanation and suggested actions.
          </Dialog.Description>

          <div className="flex items-start gap-4 mb-4">
            <div className={`p-3 rounded-full ${getSeverityColor(friendlyError.severity)}`}>
              {getIconComponent(friendlyError.icon)}
            </div>
            <div className="flex-1">
              <h2 className="text-lg font-semibold text-gray-900 dark:text-white">
                {friendlyError.title}
              </h2>
              <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
                {friendlyError.description}
              </p>
            </div>
          </div>

          {error.retry_count > 0 && (
            <div className="mb-4">
              <span className="inline-flex items-center gap-1.5 text-xs bg-blue-100 dark:bg-blue-900/30 text-blue-600 dark:text-blue-400 px-3 py-1.5 rounded-full">
                <RefreshCw className="w-3.5 h-3.5" />
                Retry attempt {error.retry_count}/{error.max_retries}
              </span>
            </div>
          )}

          <div className={`rounded-lg p-4 mb-4 ${getSeverityBgColor(friendlyError.severity)}`}>
            <div className="flex items-center gap-2 mb-2">
              <span className={`text-xs font-semibold uppercase px-2 py-0.5 rounded border ${getSeverityColor(friendlyError.severity)}`}>
                {error.error_type.replace(/_/g, ' ')}
              </span>
            </div>
            <p className="text-sm text-gray-700 dark:text-gray-300">
              {error.message}
            </p>
            <div className="flex items-center gap-1 mt-2 text-xs text-gray-500">
              <Clock size={12} />
              <span>
                {new Date(error.timestamp).toLocaleString()}
              </span>
            </div>
          </div>

          {suggestedActions.length > 0 && (
            <div className="mb-4">
              <h3 className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-2 flex items-center gap-2">
                <Settings className="w-4 h-4" />
                Suggested Actions
              </h3>
              <ul className="space-y-1.5">
                {suggestedActions.map((action, index) => (
                  <li key={index} className="flex items-start gap-2 text-sm text-gray-600 dark:text-gray-400">
                    <ChevronRight className="w-4 h-4 mt-0.5 flex-shrink-0 text-gray-400" />
                    <span>{action}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}

          <button
            onClick={() => setShowTechnicalDetails(!showTechnicalDetails)}
            className="w-full flex items-center justify-between p-3 rounded-lg border border-gray-200 dark:border-gray-600 hover:bg-gray-50 dark:hover:bg-gray-700/50 transition-colors text-sm text-gray-600 dark:text-gray-400 mb-4"
          >
            <span className="flex items-center gap-2">
              <Info className="w-4 h-4" />
              {showTechnicalDetails ? 'Hide' : 'Show'} Technical Details
            </span>
            {showTechnicalDetails ? (
              <ChevronDown className="w-4 h-4" />
            ) : (
              <ChevronRight className="w-4 h-4" />
            )}
          </button>

          {showTechnicalDetails && (
            <div className="mb-4 p-3 rounded-lg bg-gray-100 dark:bg-gray-900/50 border border-gray-200 dark:border-gray-700 text-xs font-mono overflow-x-auto">
              <div className="space-y-1 text-gray-600 dark:text-gray-400">
                <p><span className="font-semibold text-gray-800 dark:text-gray-200">Type:</span> {error.error_type}</p>
                <p><span className="font-semibold text-gray-800 dark:text-gray-200">Message:</span> {error.message}</p>
                <p><span className="font-semibold text-gray-800 dark:text-gray-200">Timestamp:</span> {error.timestamp}</p>
                <p><span className="font-semibold text-gray-800 dark:text-gray-200">Retry:</span> {error.retry_count}/{error.max_retries}</p>
                {error.context && Object.keys(error.context).length > 0 && (
                  <p><span className="font-semibold text-gray-800 dark:text-gray-200">Context:</span> {JSON.stringify(error.context, null, 2)}</p>
                )}
              </div>
              <p className="text-xs text-gray-400 mt-2 pt-2 border-t border-gray-200 dark:border-gray-700">
                Check browser console for full error details
              </p>
            </div>
          )}

          <div className="space-y-2">
            <p className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-3">
              What would you like to do?
            </p>

            {interventionOptions.retry && (
              <button
                onClick={handleRetry}
                disabled={isLoading || actionTaken !== null}
                className="w-full flex items-center gap-3 p-3 rounded-lg border border-gray-200 dark:border-gray-600 hover:bg-blue-50 dark:hover:bg-blue-900/20 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              >
                <RefreshCw className={`w-5 h-5 ${isLoading ? 'animate-spin' : ''} text-blue-500`} />
                <div className="flex-1 text-left">
                  <div className="font-medium text-gray-900 dark:text-white">Retry</div>
                  <div className="text-xs text-gray-500">Try this step again</div>
                </div>
              </button>
            )}

            {interventionOptions.skip && (
              <button
                onClick={handleSkip}
                disabled={isLoading || actionTaken !== null}
                className="w-full flex items-center gap-3 p-3 rounded-lg border border-gray-200 dark:border-gray-600 hover:bg-amber-50 dark:hover:bg-amber-900/20 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              >
                <SkipForward className="w-5 h-5 text-amber-500" />
                <div className="flex-1 text-left">
                  <div className="font-medium text-gray-900 dark:text-white">Skip Step</div>
                  <div className="text-xs text-gray-500">Continue to next step</div>
                </div>
              </button>
            )}

            <button
              onClick={handleAbort}
              disabled={isLoading || actionTaken !== null}
              className="w-full flex items-center gap-3 p-3 rounded-lg border border-gray-200 dark:border-gray-600 hover:bg-red-50 dark:hover:bg-red-900/20 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <XCircle className="w-5 h-5 text-red-500" />
              <div className="flex-1 text-left">
                <div className="font-medium text-gray-900 dark:text-white">Abort</div>
                <div className="text-xs text-gray-500">Stop the entire workflow</div>
              </div>
            </button>
          </div>

          {!actionTaken && (
            <div className="flex items-center justify-between text-xs text-gray-500 dark:text-gray-400 pt-3 mt-3 border-t border-gray-200 dark:border-gray-700">
              <span>Auto-aborting in {countdown}s</span>
              <span className={countdown <= 10 ? 'text-red-500 font-medium' : ''}>
                {countdown}s remaining
              </span>
            </div>
          )}

          {actionTaken && (
            <div className="text-center text-sm text-gray-500 dark:text-gray-400 pt-2">
              {actionTaken === 'retry' && 'Retrying the failed step...'}
              {actionTaken === 'skip' && 'Skipping to next step...'}
              {actionTaken === 'abort' && 'Aborting workflow...'}
            </div>
          )}

          {actionTaken && (
            <button
              onClick={onClose}
              className="absolute top-4 right-4 p-1.5 rounded-full hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors"
              aria-label="Close dialog"
            >
              <XCircle className="w-5 h-5 text-gray-400" />
            </button>
          )}
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  )
}
