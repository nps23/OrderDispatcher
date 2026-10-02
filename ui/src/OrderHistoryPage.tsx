import { useEffect, useState } from 'react'
import { Alert, Box, Chip, CircularProgress, Link, Paper, Stack, Typography } from '@mui/material'
import { Link as RouterLink, useParams } from 'react-router-dom'
import { API_URL, formatDate, statusColors, type Order, type OrderEvent } from './orders'

export default function OrderHistoryPage() {
  const { orderId = '' } = useParams()
  const [order, setOrder] = useState<Order | null>(null)
  const [events, setEvents] = useState<OrderEvent[] | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    let active = true

    async function load() {
      setLoading(true)
      setError('')
      try {
        const [orderResponse, eventsResponse] = await Promise.all([
          fetch(`${API_URL}/orders/${orderId}`),
          fetch(`${API_URL}/orders/${orderId}/events`),
        ])
        if (!orderResponse.ok || !eventsResponse.ok) {
          const response = !orderResponse.ok ? orderResponse : eventsResponse
          const body = (await response.json().catch(() => ({}))) as {
            detail?: string
          }
          throw new Error(
            body.detail || `Unable to load order history (${response.status}).`,
          )
        }
        const [orderData, eventData] = await Promise.all([
          orderResponse.json() as Promise<Order>,
          eventsResponse.json() as Promise<OrderEvent[]>,
        ])
        if (active) {
          setOrder(orderData)
          setEvents(eventData)
        }
      } catch (cause) {
        if (active) {
          setError(
            cause instanceof TypeError
              ? `Could not reach ${API_URL}. Check that the backend is running.`
              : cause instanceof Error
                ? cause.message
                : 'Unable to load order history.',
          )
        }
      } finally {
        if (active) setLoading(false)
      }
    }

    void load()
    return () => {
      active = false
    }
  }, [orderId])

  return (
    <Box component="main" className="app-main history-main">
      <Link component={RouterLink} to="/orders" className="back-link">
        ← Back to orders
      </Link>
      {loading ? (
        <CircularProgress className="history-loading" />
      ) : error ? (
        <Alert severity="error">{error}</Alert>
      ) : order ? (
        <>
          <Stack className="history-heading">
            <Box>
              <Typography component="h1" variant="h5">
                Order #{order.source_order_id}
              </Typography>
              <Typography color="text.secondary" variant="body2">
                Order ID: {order.id}
              </Typography>
            </Box>
            <Chip
              size="small"
              variant="outlined"
              color={statusColors[order.status]}
              label={
                order.status === 'received'
                  ? 'New'
                  : order.status[0].toUpperCase() + order.status.slice(1)
              }
            />
          </Stack>

          <Paper variant="outlined" className="history-summary">
            <Typography variant="subtitle2">Order details</Typography>
            <Typography color="text.secondary" variant="body2">
              Created {formatDate(order.created_at)}
            </Typography>
            {order.scheduled_for && (
              <Typography color="text.secondary" variant="body2">
                Scheduled for {formatDate(order.scheduled_for)}
              </Typography>
            )}
            <Typography color="text.secondary" variant="body2">
              Items: {order.items.map((item) => item.name).join(', ') || 'None'}
            </Typography>
          </Paper>

          <Typography component="h2" variant="h6" className="history-title">
            Order history
          </Typography>
          {events?.length ? (
            <Stack className="history-events">
              {events.map((event) => (
                <Paper key={event.id} variant="outlined" className="history-event">
                  <Stack className="history-event-heading">
                    <Typography variant="subtitle2">
                      {event.event_type
                        .replaceAll('_', ' ')
                        .replace(/\b\w/g, (letter) => letter.toUpperCase())}
                    </Typography>
                    <Typography variant="caption" color="text.secondary">
                      {formatDate(event.occurred_at)}
                    </Typography>
                  </Stack>
                  <Typography variant="caption" color="text.secondary">
                    Source: {event.ingestion_source ?? 'System'}
                  </Typography>
                  {Object.keys(event.details).length > 0 && (
                    <Box component="pre" className="event-details">
                      {JSON.stringify(event.details, null, 2)}
                    </Box>
                  )}
                </Paper>
              ))}
            </Stack>
          ) : (
            <Typography color="text.secondary">No history events recordd.</Typography>
          )}
        </>
      ) : null}
    </Box>
  )
}
