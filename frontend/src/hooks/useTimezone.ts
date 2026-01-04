import { useState, useEffect, useCallback } from 'react'
import { useSettingsStore } from '../stores/settingsStore'
import { formatDistanceToNow, format, parseISO } from 'date-fns'

export type TimezoneMode = 'auto' | string

export interface TimezoneState {
  timezone: string
  offset: string
  formattedCurrentTime: string
  isAutoDetected: boolean
}

export function useTimezone() {
  const { general, updateConfig } = useSettingsStore()
  const [state, setState] = useState<TimezoneState>({
    timezone: general.timezone || 'auto',
    offset: '+00:00',
    formattedCurrentTime: '',
    isAutoDetected: general.timezone === 'auto',
  })

  const detectBrowserTimezone = useCallback((): string => {
    try {
      return Intl.DateTimeFormat().resolvedOptions().timeZone
    } catch {
      return 'UTC'
    }
  }, [])

  const updateTimezoneInfo = useCallback((tz: string) => {
    try {
      const now = new Date()
      const offset = now.toLocaleString('en-US', {
        timeZone: tz,
        timeZoneName: 'shortOffset',
      })
      const offsetMatch = offset.match(/UTC([+-]\d{2}:?\d{2})?/)
      const offsetStr = offsetMatch ? offsetMatch[1] || '+00:00' : '+00:00'

      setState({
        timezone: tz,
        offset: offsetStr,
        formattedCurrentTime: now.toLocaleString('en-US', {
          timeZone: tz,
          year: 'numeric',
          month: 'short',
          day: 'numeric',
          hour: '2-digit',
          minute: '2-digit',
          second: '2-digit',
        }),
        isAutoDetected: false,
      })
    } catch {
      setState(prev => ({
        ...prev,
        timezone: 'UTC',
        offset: '+00:00',
        formattedCurrentTime: new Date().toISOString(),
        isAutoDetected: false,
      }))
    }
  }, [])

  useEffect(() => {
    if (state.timezone === 'auto') {
      const detected = detectBrowserTimezone()
      updateTimezoneInfo(detected)
    } else {
      updateTimezoneInfo(state.timezone)
    }
  }, [state.timezone, detectBrowserTimezone, updateTimezoneInfo])

  useEffect(() => {
    const interval = setInterval(() => {
      if (state.timezone === 'auto') {
        const detected = detectBrowserTimezone()
        updateTimezoneInfo(detected)
      } else {
        updateTimezoneInfo(state.timezone)
      }
    }, 60000)
    return () => clearInterval(interval)
  }, [state.timezone, detectBrowserTimezone, updateTimezoneInfo])

  const setTimezone = useCallback(async (timezone: string) => {
    setState(prev => ({ ...prev, timezone }))
    await updateConfig({ general: { ...general, timezone } })
  }, [general, updateConfig])

  return {
    ...state,
    setTimezone,
    detectBrowserTimezone,
  }
}

export function useRelativeTime() {
  const { timezone } = useTimezone()

  const formatRelative = useCallback((dateString: string): string => {
    try {
      const date = parseISO(dateString)
      return formatDistanceToNow(date, { addSuffix: true })
    } catch {
      return 'unknown time'
    }
  }, [])

  const formatDateTime = useCallback((
    dateString: string,
    formatStr: 'short' | 'medium' | 'long' | 'full' = 'medium'
  ): string => {
    try {
      const date = parseISO(dateString)
      const formats: Record<string, string> = {
        short: 'MMM d, yyyy',
        medium: 'MMM d, yyyy h:mm a',
        long: 'MMMM d, yyyy h:mm a',
        full: 'EEEE, MMMM d, yyyy h:mm a zzz',
      }
      return format(date, formats[formatStr])
    } catch {
      return dateString
    }
  }, [])

  const formatInTimezone = useCallback((
    dateString: string,
    formatStr: string = 'MMM d, yyyy h:mm a'
  ): string => {
    try {
      const date = parseISO(dateString)
      return format(date, formatStr)
    } catch {
      return dateString
    }
  }, [])

  return {
    formatRelative,
    formatDateTime,
    formatInTimezone,
  }
}

export function useTimezoneSelectOptions() {
  const commonTimezones = [
    { value: 'auto', label: 'Auto-detect' },
    { value: 'UTC', label: 'UTC' },
    { value: 'America/New_York', label: 'Eastern Time (US)' },
    { value: 'America/Chicago', label: 'Central Time (US)' },
    { value: 'America/Denver', label: 'Mountain Time (US)' },
    { value: 'America/Los_Angeles', label: 'Pacific Time (US)' },
    { value: 'America/Anchorage', label: 'Alaska Time' },
    { value: 'Pacific/Honolulu', label: 'Hawaii Time' },
    { value: 'Europe/London', label: 'London (GMT/BST)' },
    { value: 'Europe/Paris', label: 'Central European (CET)' },
    { value: 'Europe/Berlin', label: 'Berlin (CET)' },
    { value: 'Europe/Moscow', label: 'Moscow (MSK)' },
    { value: 'Asia/Dubai', label: 'Dubai (GST)' },
    { value: 'Asia/Kolkata', label: 'India (IST)' },
    { value: 'Asia/Bangkok', label: 'Bangkok (ICT)' },
    { value: 'Asia/Singapore', label: 'Singapore (SGT)' },
    { value: 'Asia/Tokyo', label: 'Tokyo (JST)' },
    { value: 'Asia/Shanghai', label: 'China (CST)' },
    { value: 'Australia/Sydney', label: 'Sydney (AEST)' },
    { value: 'Australia/Perth', label: 'Perth (AWST)' },
    { value: 'Pacific/Auckland', label: 'New Zealand (NZST)' },
  ]

  return commonTimezones
}
