interface SkeletonProps {
  className?: string
}

export function Skeleton({ className = '' }: SkeletonProps) {
  return (
    <div
      className={`animate-pulse bg-muted rounded ${className}`}
    />
  )
}

export function SkeletonText({ lines = 1 }: { lines?: number }) {
  return (
    <div className="space-y-2">
      {Array.from({ length: lines }).map((_, i) => (
        <Skeleton
          key={i}
          className={i === lines - 1 && lines > 1 ? 'w-3/4' : 'w-full'}
        />
      ))}
    </div>
  )
}

export function SkeletonAvatar({ size = 'md' }: { size?: 'sm' | 'md' | 'lg' }) {
  const sizeClasses = {
    sm: 'w-8 h-8',
    md: 'w-10 h-10',
    lg: 'w-12 h-12'
  }

  return (
    <Skeleton className={`rounded-full ${sizeClasses[size]}`} />
  )
}

export function SkeletonButton({ className = '' }: { className?: string }) {
  return (
    <Skeleton className={`h-10 rounded-lg ${className}`} />
  )
}

export function SkeletonCard() {
  return (
    <div className="p-4 border rounded-lg space-y-3">
      <div className="flex items-center gap-3">
        <SkeletonAvatar size="sm" />
        <div className="flex-1 space-y-2">
          <Skeleton className="h-4 w-3/4" />
          <Skeleton className="h-3 w-1/2" />
        </div>
      </div>
      <SkeletonText lines={2} />
    </div>
  )
}

export function SkeletonMessage() {
  return (
    <div className="flex gap-3 p-3">
      <SkeletonAvatar size="md" />
      <div className="flex-1 space-y-2">
        <Skeleton className="h-4 w-32" />
        <SkeletonText lines={3} />
      </div>
    </div>
  )
}

export function SkeletonSessionItem() {
  return (
    <div className="flex items-center gap-2 px-3 py-2 text-sm rounded-lg">
      <Skeleton className="w-4 h-4 rounded" />
      <div className="flex-1 space-y-1">
        <Skeleton className="h-4 w-3/4" />
        <Skeleton className="h-3 w-1/2" />
      </div>
    </div>
  )
}

export function SkeletonSettingsField() {
  return (
    <div className="space-y-1">
      <Skeleton className="h-4 w-24" />
      <Skeleton className="h-10 w-full" />
    </div>
  )
}

export function SkeletonSettingsTab() {
  return (
    <div className="space-y-6">
      <div className="space-y-4">
        <Skeleton className="h-6 w-48" />
        <div className="grid grid-cols-2 gap-4">
          <SkeletonSettingsField />
          <SkeletonSettingsField />
          <SkeletonSettingsField />
          <SkeletonSettingsField />
        </div>
      </div>
      <div className="space-y-1">
        <Skeleton className="h-4 w-32" />
        <Skeleton className="h-24 w-full" />
      </div>
    </div>
  )
}

export function SkeletonChatContainer() {
  return (
    <div className="flex-1 flex flex-col">
      <div className="flex-1 flex flex-col items-center justify-center p-8">
        <div className="w-20 h-20 bg-muted rounded-2xl mb-6 animate-pulse" />
        <div className="h-8 w-64 bg-muted rounded mb-2 animate-pulse" />
        <div className="h-4 w-96 bg-muted rounded animate-pulse" />
      </div>
      <div className="p-6 border-t">
        <div className="flex gap-4 mb-6">
          {Array.from({ length: 4 }).map((_, i) => (
            <div key={i} className="flex-1 h-32 bg-muted rounded-lg animate-pulse" />
          ))}
        </div>
        <div className="h-16 bg-muted rounded-lg animate-pulse" />
      </div>
    </div>
  )
}

export function SkeletonMessageList() {
  return (
    <div className="flex-1 overflow-auto p-4 space-y-4">
      {Array.from({ length: 3 }).map((_, i) => (
        <SkeletonMessage key={i} />
      ))}
    </div>
  )
}

export function SkeletonSessionList() {
  return (
    <div className="flex-1 flex flex-col overflow-hidden">
      <div className="p-4 border-b space-y-3">
        <Skeleton className="h-10 w-full rounded-lg" />
        <Skeleton className="h-10 w-full rounded-lg" />
      </div>
      <div className="flex-1 overflow-auto p-2 space-y-1">
        {Array.from({ length: 5 }).map((_, i) => (
          <SkeletonSessionItem key={i} />
        ))}
      </div>
    </div>
  )
}
