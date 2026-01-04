import { create } from 'zustand'
import { persist } from 'zustand/middleware'

export interface ErrorDetails {
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

export interface InterventionOptions {
  retry: boolean
  skip: boolean
  abort: boolean
}

export interface PendingError {
  error: ErrorDetails
  step_info?: {
    type: string
    description: string
    step_number: number
  }
  intervention_options: InterventionOptions
  timestamp: string
}

interface ChatErrorState {
  // Error handling state
  pendingError: PendingError | null
  isAwaitingIntervention: boolean
  errorInterventionAction: string | null

  // Actions
  setPendingError: (error: PendingError | null) => void
  setAwaitingIntervention: (awaiting: boolean) => void
  setErrorInterventionAction: (action: string | null) => void
  clearErrorState: () => void
}

export const useChatErrorStore = create<ChatErrorState>()(
  persist(
    (set) => ({
      // Initial error handling state
      pendingError: null,
      isAwaitingIntervention: false,
      errorInterventionAction: null,

      // Error handling actions
      setPendingError: (error) => set({ 
        pendingError: error,
        isAwaitingIntervention: error !== null,
      }),
      
      setAwaitingIntervention: (awaiting) => set({ 
        isAwaitingIntervention: awaiting,
        // Clear error if no longer awaiting
        pendingError: awaiting ? undefined : null,
      }),
      
      setErrorInterventionAction: (action) => set({ 
        errorInterventionAction: action,
        isAwaitingIntervention: false,
      }),
      
      clearErrorState: () => set({
        pendingError: null,
        isAwaitingIntervention: false,
        errorInterventionAction: null,
      }),
    }),
    {
      name: 'chat-error-storage',
      partialize: (state) => ({
        // Don't persist error state - it should be session-specific
        pendingError: undefined,
        isAwaitingIntervention: undefined,
        errorInterventionAction: undefined,
      })
    }
  )
)
