import { AlertTriangle, RefreshCw, SkipForward, XCircle, Clock } from 'lucide-react'
import * as Dialog from '@radix-ui/react-dialog'
import { useState, useEffect } from 'react'

interface ErrorDetails {
  error_type: string
  message: string
  timestamp: string
  retry_count: number
  max_retries: number
  can_retry: boolean
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
  sessionId: string
  onRetry: () => void
  onSkip: () => void
  onAbort: () => void
  isLoading?: boolean
}

export default function ErrorModal({
  isOpen,
  onClose,
  error,
  interventionOptions,
  sessionId,
  onRetry,
  onSkip,
  onAbort,
  isLoading = false,
}: ErrorModalProps) {
  const [countdown, setCountdown] = useState(60) // 60 second timeout
  const [actionTaken, setActionTaken] = useState<string | null>(null)

  // Countdown timer for timeout
  useEffect(() => {
    if (!isOpen || actionTaken) return

    const timer = setInterval(() => {
      setCountdown((prev) => {
        if (prev <= 1) {
          // Auto-abort on timeout
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

  const getErrorTypeLabel = (type: string) => {
    const labels: Record<string, string> = {
      api_error: 'API Error',
      api_auth: 'Authentication Failed',
      api_rate_limit: 'Rate Limited',
      api_timeout: 'API Timeout',
      api_unavailable: 'Service Unavailable',
      network_error: 'Network Error',
      connection_timeout: 'Connection Timeout',
      validation_error: 'Validation Error',
      schema_error: 'Schema Error',
      execution_timeout: 'Execution Timeout',
      execution_error: 'Execution Error',
      memory_error: 'Out of Memory',
      data_not_found: 'Data Not Found',
      data_corruption: 'Data Corruption',
      system_error: 'System Error',
      unknown_error: 'Unknown Error',
    }
    return labels[type] || 'Error'
  }

  const getErrorTypeColor = (type: string) => {
    if (type.includes('auth') || type.includes('rate')) return 'text-yellow-500'
    if (type.includes('timeout') || type.includes('network')) return 'text-orange-500'
    if (type.includes('error') || type.includes('validation')) return 'text-red-500'
    return 'text-gray-500'
  }

  if (!error) return null

  return (
    <Dialog.Root open={isOpen} onOpenChange={(open) => !open && onClose()}>
      <Dialog.Portal>
        <Dialog.Overlay className="fixed inset-0 bg-black/50 backdrop-blur-sm z-50" />
        <Dialog.Content className="fixed left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 bg-white dark:bg-gray-800 rounded-xl shadow-2xl max-w-md w-full mx-4 p-6 z-50 animate-in fade-in zoom-in-95 duration-200">
          {/* Header */}
          <div className="flex items-center gap-3 mb-4">
            <div className="p-2 rounded-full bg-red-100 dark:bg-red-900/30">
              <AlertTriangle className="w-6 h-6 text-red-500" />
            </div>
            <div>
              <Dialog.Title className="text-lg font-semibold text-gray-900 dark:text-white">
                {getErrorTypeLabel(error.error_type)}
              </Dialog.Title>
              <Dialog.Description className="text-sm text-gray-500 dark:text-gray-400">
                An error occurred during execution
              </Dialog.Description>
            </div>
          </div>

          {/* Error Details */}
          <div className="bg-gray-50 dark:bg-gray-700/50 rounded-lg p-4 mb-4">
            <div className="flex items-center gap-2 mb-2">
              <span className={`text-sm font-medium ${getErrorTypeColor(error.error_type)}`}>
                {error.error_type.replace(/_/g, ' ').toUpperCase()}
              </span>
              {error.retry_count > 0 && (
                <span className="text-xs bg-blue-100 dark:bg-blue-900/30 text-blue-600 dark:text-blue-400 px-2 py-0.5 rounded">
                  Retry {error.retry_count}/{error.max_retries}
                </span>
              )}
            </div>
            <p className="text-sm text-gray-700 dark:text-gray-300">
              {error.message}
            </p>
            <div className="flex items-center gap-1 mt-2 text-xs text-gray-500">
              <Clock size={12} />
              <span>
                {new Date(error.timestamp).toLocaleTimeString()}
              </span>
            </div>
          </div>

          {/* Intervention Options */}
          <div className="space-y-2 mb-4">
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
                className="w-full flex items-center gap-3 p-3 rounded-lg border border-gray-200 dark:border-gray-600 hover:bg-yellow-50 dark:hover:bg-yellow-900/20 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              >
                <SkipForward className="w-5 h-5 text-yellow-500" />
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

          {/* Timeout Warning */}
          {!actionTaken && (
            <div className="flex items-center justify-between text-xs text-gray-500 dark:text-gray-400 pt-2 border-t border-gray-200 dark:border-gray-700">
              <span>Auto-aborting in {countdown}s</span>
              <span className={countdown <= 10 ? 'text-red-500' : ''}>
                {countdown}s remaining
              </span>
            </div>
          )}

          {/* Action Taken Message */}
          {actionTaken && (
            <div className="text-center text-sm text-gray-500 dark:text-gray-400 pt-2">
              {actionTaken === 'retry' && 'Retrying the failed step...'}
              {actionTaken === 'skip' && 'Skipping to next step...'}
              {actionTaken === 'abort' && 'Aborting workflow...'}
            </div>
          )}

          {/* Close button (only when action taken) */}
          {actionTaken && (
            <button
              onClick={onClose}
              className="absolute top-4 right-4 p-1 rounded-full hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors"
            >
              <XCircle className="w-5 h-5 text-gray-400" />
            </button>
          )}
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  )
}
