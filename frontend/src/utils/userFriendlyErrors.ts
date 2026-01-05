export type ErrorType =
  | 'api_error'
  | 'api_auth'
  | 'api_rate_limit'
  | 'api_timeout'
  | 'api_unavailable'
  | 'network_error'
  | 'connection_timeout'
  | 'validation_error'
  | 'schema_error'
  | 'execution_timeout'
  | 'execution_error'
  | 'memory_error'
  | 'data_not_found'
  | 'data_corruption'
  | 'system_error'
  | 'unknown_error'

export interface UserFriendlyError {
  title: string
  description: string
  suggestion: string
  severity: 'info' | 'warning' | 'error'
  icon: string
}

export interface TechnicalDetails {
  errorType: string
  originalMessage: string
  timestamp: string
  retryCount: number
  maxRetries: number
  context?: Record<string, unknown>
  stackTrace?: string
}

const errorMessages: Record<ErrorType, UserFriendlyError> = {
  api_timeout: {
    title: 'AI Response Delayed',
    description: 'The AI is taking longer than expected to respond. This can happen during high-traffic periods.',
    suggestion: 'Try again in a few moments. If the issue persists, the service may be experiencing high demand.',
    severity: 'warning',
    icon: 'clock',
  },
  api_rate_limit: {
    title: 'Too Many Requests',
    description: "You've made too many requests in a short time. The service needs a moment to catch up.",
    suggestion: 'Please wait a moment before trying again. This helps ensure everyone gets a smooth experience.',
    severity: 'warning',
    icon: 'alert',
  },
  api_auth: {
    title: 'Authentication Issue',
    description: 'There seems to be an issue with the API authentication. This is usually a configuration problem.',
    suggestion: 'Please check your API settings and ensure your API keys are correctly configured.',
    severity: 'error',
    icon: 'lock',
  },
  api_unavailable: {
    title: 'Service Temporarily Unavailable',
    description: 'The AI service is temporarily unavailable. This is usually a temporary issue on their end.',
    suggestion: 'Please wait a moment and try again. The service typically recovers quickly.',
    severity: 'error',
    icon: 'alert',
  },
  network_error: {
    title: 'Network Connection Issue',
    description: 'There was a problem connecting to the service. Your internet connection may be unstable.',
    suggestion: 'Check your internet connection and try again. If the problem continues, the service may be experiencing issues.',
    severity: 'warning',
    icon: 'wifi',
  },
  connection_timeout: {
    title: 'Connection Timed Out',
    description: 'The connection to the service took too long and was closed. This can happen during network issues.',
    suggestion: 'Check your internet connection and try again. Consider trying at a different time if issues persist.',
    severity: 'warning',
    icon: 'clock',
  },
  api_error: {
    title: 'Service Error',
    description: 'The AI service returned an unexpected error. This is usually a temporary issue.',
    suggestion: 'Try again in a few moments. If the problem persists, the service may be experiencing temporary difficulties.',
    severity: 'error',
    icon: 'alert',
  },
  validation_error: {
    title: 'Invalid Input',
    description: 'The request contained invalid data that could not be processed.',
    suggestion: 'Try rephrasing your request or removing special characters that might cause issues.',
    severity: 'error',
    icon: 'alert',
  },
  schema_error: {
    title: 'Data Processing Error',
    description: 'There was an error processing the response from the AI service.',
    suggestion: 'Try again. If the problem persists, the service may be experiencing temporary difficulties.',
    severity: 'error',
    icon: 'alert',
  },
  execution_timeout: {
    title: 'Operation Took Too Long',
    description: 'The operation exceeded the maximum allowed time and was stopped.',
    suggestion: 'Try a simpler request or break it into smaller parts. Complex operations may need more time.',
    severity: 'warning',
    icon: 'clock',
  },
  execution_error: {
    title: 'Execution Failed',
    description: 'The requested operation could not be completed successfully.',
    suggestion: 'Review your request for any errors and try again. If this is code execution, check for syntax issues.',
    severity: 'error',
    icon: 'alert',
  },
  memory_error: {
    title: 'Resource Limit Reached',
    description: 'The operation required more memory than available. This is a resource limitation.',
    suggestion: 'Try a simpler request or one that requires less processing. Complex operations may need to be broken down.',
    severity: 'error',
    icon: 'alert',
  },
  data_not_found: {
    title: 'Data Not Found',
    description: 'The requested data could not be found. It may have been removed or never existed.',
    suggestion: 'Verify the information you\'re looking for and try a different query. The data may need to be fetched again.',
    severity: 'info',
    icon: 'search',
  },
  data_corruption: {
    title: 'Data Integrity Issue',
    description: 'The data appears to be corrupted or incomplete.',
    suggestion: 'Try again. If the problem persists, the data may need to be refreshed or reloaded.',
    severity: 'error',
    icon: 'alert',
  },
  system_error: {
    title: 'System Error',
    description: 'An unexpected error occurred in the system. This is not your fault.',
    suggestion: 'Please try again. If the problem persists, there may be a temporary system issue.',
    severity: 'error',
    icon: 'alert',
  },
  unknown_error: {
    title: 'Something Went Wrong',
    description: 'An unexpected error occurred. We\'re not sure what caused it.',
    suggestion: 'Try again. If the problem persists, please check your connection and try again later.',
    severity: 'error',
    icon: 'alert',
  },
}

export function getUserFriendlyError(
  errorType: string,
  originalMessage?: string,
  _context?: Record<string, unknown>
): UserFriendlyError {
  const type = errorType as ErrorType
  const friendlyError = errorMessages[type] || errorMessages.unknown_error

  if (originalMessage && !friendlyError.description.includes(originalMessage)) {
    return {
      ...friendlyError,
      description: `${friendlyError.description} (Original: ${originalMessage})`,
    }
  }

  return friendlyError
}

export function createTechnicalDetails(
  errorType: string,
  originalMessage: string,
  timestamp: string,
  retryCount: number,
  maxRetries: number,
  context?: Record<string, unknown>,
  stackTrace?: string
): TechnicalDetails {
  return {
    errorType,
    originalMessage,
    timestamp,
    retryCount,
    maxRetries,
    context,
    stackTrace,
  }
}

export function logErrorToConsole(details: TechnicalDetails): void {
  console.group('🚨 Error Details (for debugging)')
  console.error('Error Type:', details.errorType)
  console.error('Original Message:', details.originalMessage)
  console.error('Timestamp:', details.timestamp)
  console.error('Retry Count:', `${details.retryCount}/${details.maxRetries}`)
  if (details.context && Object.keys(details.context).length > 0) {
    console.error('Context:', details.context)
  }
  if (details.stackTrace) {
    console.error('Stack Trace:', details.stackTrace)
  }
  console.groupEnd()
}

export function getSuggestedActions(errorType: string): string[] {
  const actions: Record<ErrorType, string[]> = {
    api_timeout: [
      'Wait a moment and retry',
      'Try a simpler request',
      'Check if the service is experiencing issues',
    ],
    api_rate_limit: [
      'Wait before sending more requests',
      'Reduce the frequency of your requests',
      'Try again in a few minutes',
    ],
    api_auth: [
      'Check your API keys in settings',
      'Verify your API key is valid and has the required permissions',
      'Contact support if the issue persists',
    ],
    api_unavailable: [
      'Wait and try again later',
      'Check service status pages',
      'Try an alternative provider if configured',
    ],
    network_error: [
      'Check your internet connection',
      'Refresh the page',
      'Try again in a few moments',
    ],
    connection_timeout: [
      'Check your internet connection',
      'Try a simpler request',
      'Wait and retry',
    ],
    api_error: [
      'Retry the request',
      'Try again in a few moments',
      'If persistent, check service status',
    ],
    validation_error: [
      'Review your input for errors',
      'Remove special characters',
      'Try rephrasing your request',
    ],
    schema_error: [
      'Retry the request',
      'Try a simpler query',
      'If persistent, contact support',
    ],
    execution_timeout: [
      'Try a simpler request',
      'Break complex tasks into smaller steps',
      'Reduce the scope of your request',
    ],
    execution_error: [
      'Review your code for errors',
      'Check syntax and logic',
      'Try a simpler operation',
    ],
    memory_error: [
      'Try a simpler request',
      'Reduce the amount of data processed',
      'Break complex operations into smaller parts',
    ],
    data_not_found: [
      'Verify the data exists',
      'Try a different query',
      'Check if the data needs to be reloaded',
    ],
    data_corruption: [
      'Try reloading the data',
      'Refresh the page',
      'Try again later',
    ],
    system_error: [
      'Refresh the page',
      'Try again in a few moments',
      'Contact support if the issue persists',
    ],
    unknown_error: [
      'Try again',
      'Refresh the page',
      'Check your connection',
    ],
  }

  const type = errorType as ErrorType
  return actions[type] || actions.unknown_error
}
