import { useEffect } from 'react'
import { useSettingsStore } from '../stores/settingsStore'

export function useSettings() {
  const store = useSettingsStore()
  
  useEffect(() => {
    store.loadConfig()
  }, [store.loadConfig])
  
  return store
}
