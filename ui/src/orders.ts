export type Status = 'received' | 'scheduled' | 'dispatched' | 'cancelled'

export type Order = {
  id: string
  source_order_id: string
  status: Status
  scheduled_for: string | null
  created_at: string
  items: {
    id: string
    name: string
  }[]
}

export type OrderEvent = {
  id: string
  event_type: string
  ingestion_source: string | null
  details: Record<string, unknown>
  occurred_at: string
}

export const API_URL = 'http://localhost:9000'

export const statusColors = {
  received: 'warning',
  scheduled: 'info',
  dispatched: 'success',
  cancelled: 'error',
} as const

export function formatDate(value: string) {
  const date = new Date(value)
  return Number.isNaN(date.getTime())
    ? value
    : new Intl.DateTimeFormat('en-US', {
        month: 'short',
        day: 'numeric',
        year: 'numeric',
        hour: 'numeric',
        minute: '2-digit',
      }).format(date)
}
