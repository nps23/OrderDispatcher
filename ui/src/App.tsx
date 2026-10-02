import { useEffect, useState } from 'react'
import { Activity, RefreshCw, Search } from 'lucide-react'
import { DataGrid } from '@mui/x-data-grid'
import type { GridColDef } from '@mui/x-data-grid'
import {
  Alert,
  Box,
  Button,
  Chip,
  CircularProgress,
  CssBaseline,
  InputAdornment,
  Paper,
  Stack,
  Tab,
  Tabs,
  TextField,
  ThemeProvider,
  Typography,
  createTheme,
} from '@mui/material'

type Status = 'received' | 'scheduled' | 'dispatched' | 'cancelled'

type Order = {
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

const API_URL = 'http://localhost:9000'
const PAGE_SIZE = 25

const filters = [
  ['all', 'All orders'],
  ['received', 'New'],
  ['scheduled', 'Scheduled'],
  ['dispatched', 'Dispatched'],
  ['cancelled', 'Cancelled'],
] as const

const snapshot = [
  ['received', 'New', '#bd794c'],
  ['scheduled', 'Scheduled', '#6584b1'],
  ['dispatched', 'Dispatched', '#56815f'],
] as const

const statusColors = {
  received: 'warning',
  scheduled: 'info',
  dispatched: 'success',
  cancelled: 'error',
} as const

const theme = createTheme({
  palette: {
    mode: 'dark',
    primary: { main: '#ffa200' },
    background: { default: '#141711', paper: '#19211c' },
    text: { primary: '#eaebe4', secondary: '#9ba99e' },
    divider: '#303c33',
  },
  shape: { borderRadius: 8 },
  typography: {
    fontFamily:
      'Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif',
    h5: { fontWeight: 700 },
    subtitle2: { fontWeight: 700 },
    button: { textTransform: 'none', fontWeight: 600 },
  },
  components: {
    MuiPaper: {
      styleOverrides: {
        outlined: { borderColor: '#303c33' },
      },
    },
    MuiTab: {
      styleOverrides: {
        root: {
          minHeight: 48,
          minWidth: 0,
          paddingLeft: 10,
          paddingRight: 10,
          textTransform: 'none',
        },
      },
    },
  },
})

const columns: GridColDef<Order>[] = [
  {
    field: 'source_order_id',
    headerName: 'Order',
    minWidth: 250,
    flex: 1,
    renderCell: ({ row }) => (
      <Box className="order-identifiers">
        <Typography variant="subtitle2" title={row.source_order_id}>
          #{row.source_order_id}
        </Typography>
        <Typography variant="caption" color="text.secondary" title={row.id}>
          {row.id}
        </Typography>
      </Box>
    ),
  },
  {
    field: 'items',
    headerName: 'Items',
    minWidth: 190,
    flex: 1.4,
    sortable: false,
    valueGetter: (_value, row) => row.items.map(({ name }) => name).join(', '),
    renderCell: ({ row }) => (
      <Box className="order-items">
        <Typography variant="body2" noWrap>
          {row.items[0]?.name || 'No item details'}
        </Typography>
        {row.items.length > 1 && (
          <Typography variant="caption" color="text.secondary">
            +{row.items.length - 1} more
          </Typography>
        )}
      </Box>
    ),
  },
  {
    field: 'status',
    headerName: 'Status',
    minWidth: 130,
    renderCell: ({ row }) => (
      <Chip
        size="small"
        variant="outlined"
        color={statusColors[row.status]}
        label={
          row.status === 'received'
            ? 'New'
            : row.status[0].toUpperCase() + row.status.slice(1)
        }
      />
    ),
  },
  {
    field: 'scheduled_for',
    headerName: 'Scheduled for',
    minWidth: 180,
    flex: 1,
    valueFormatter: (value) => (value ? formatDate(value) : '—'),
  },
  {
    field: 'created_at',
    headerName: 'Created',
    minWidth: 180,
    flex: 1,
    valueFormatter: formatDate,
  },
]

export default function App() {
  const [orders, setOrders] = useState<Order[] | null>(null)
  const [snapshotOrders, setSnapshotOrders] = useState<Order[] | null>(null)
  const [status, setStatus] = useState<string>('all')
  const [search, setSearch] = useState('')
  const [offset, setOffset] = useState(0)
  const [refresh, setRefresh] = useState(0)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  // paginated search for the grid
  useEffect(() => {
    let active = true
    const params = new URLSearchParams({
      offset: String(offset),
      limit: String(PAGE_SIZE + 1),
    })

    if (status !== 'all') params.set('status', status)

    async function load() {
      setLoading(true)
      setError('')
      try {
        const response = await fetch(`${API_URL}/orders?${params}`)

        if (!response.ok) {
          const body = (await response.json().catch(() => ({}))) as {
            detail?: string
          }
          throw new Error(body.detail || `Unable to load orders (${response.status}).`)
        }

        if (active) {
          const results = (await response.json()) as Order[]
          setOrders(results)
          if (status === 'all') setSnapshotOrders(results)
        }
      } catch (cause) {
        if (active) {
          setError(
            cause instanceof TypeError
              ? `Could not reach ${API_URL}. Check that the backend is running.`
              : cause instanceof Error
                ? cause.message
                : 'Unable to load orders.',
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
  }, [offset, status, refresh])

  // TODO: Make this cleaner with state management that polls orders
  useEffect(() => {
    const timer = window.setInterval(() => setRefresh((value) => value + 1), 30_000)

    return () => window.clearInterval(timer)
  }, [])

  const pageOrders = orders?.slice(0, PAGE_SIZE) ?? []
  const query = search.trim().toLowerCase()
  const rows = query
    ? pageOrders.filter((order) =>
        [order.id, order.source_order_id, ...order.items.map(({ name }) => name)]
          .join(' ')
          .toLowerCase()
          .includes(query),
      )
    : pageOrders
  const snapshotPage = snapshotOrders?.slice(0, PAGE_SIZE) ?? []
  const counts = Object.fromEntries(
    snapshot.map(([key]) => [
      key,
      snapshotPage.filter((order) => order.status === key).length,
    ]),
  ) as Record<(typeof snapshot)[number][0], number>
  const update = () => setRefresh((value) => value + 1)

  return (
    <ThemeProvider theme={theme}>
      <CssBaseline />
      <Box className="app-shell">
        <Box component="header" className="app-header">
          <Typography component="a" href="/orders" color="text.primary" className="brand">
            Order dispatch
          </Typography>
          <Button
            size="small"
            href={`${API_URL}/docs`}
            target="_blank"
            rel="noreferrer"
          >
            API docs
          </Button>
        </Box>

        <Box component="main" className="app-main">
          <Stack className="page-heading">
            <Box>
              <Typography component="h1" variant="h5">
                Orders
              </Typography>
              <Typography color="text.secondary" variant="body2">
                Browse and filter incoming orders.
              </Typography>
            </Box>
            <Button
              variant="outlined"
              onClick={update}
              disabled={loading}
              startIcon={
                loading ? <CircularProgress size={16} /> : <RefreshCw size={16} />
              }
            >
              Refresh
            </Button>
          </Stack>

          <Paper variant="outlined" className="queue-snapshot">
            <Stack className="snapshot-row">
              <Stack className="snapshot-label">
                <Activity size={17} color="#83b58c" />
                <Box>
                  <Typography variant="subtitle2">Queue snapshot</Typography>
                  <Typography color="text.secondary" variant="caption">All-orders page</Typography>
                </Box>
              </Stack>
              {snapshot.map(([key, label]) => (
                <Stack key={key} className="snapshot-item">
                  <Box className={`snapshot-dot snapshot-dot-${key}`} />
                  <Typography color="text.secondary" variant="caption">
                    {label}
                  </Typography>
                  <Typography variant="subtitle2" className="snapshot-count">
                    {snapshotOrders === null ? '—' : counts[key]}
                  </Typography>
                </Stack>
              ))}
              <Typography
                color="text.secondary"
                variant="caption"
                className="snapshot-update"
              >
                Updates every 30 sec
              </Typography>
            </Stack>
          </Paper>

          <Paper variant="outlined" className="orders-panel">
            <Stack className="orders-toolbar">
              <Tabs
                value={status}
                onChange={(_, value: string) => {
                  setStatus(value)
                  setOffset(0)
                }}
                variant="scrollable"
                scrollButtons={false}
                aria-label="Filter orders"
              >
                {filters.map(([value, label]) => (
                  <Tab key={value} value={value} label={label} />
                ))}
              </Tabs>
              <TextField
                size="small"
                placeholder="Search this page"
                value={search}
                onChange={(event) => setSearch(event.target.value)}
                slotProps={{
                  htmlInput: { 'aria-label': 'Search orders on this page' },
                  input: {
                    startAdornment: (
                      <InputAdornment position="start">
                        <Search size={16} />
                      </InputAdornment>
                    ),
                  },
                }}
                className="orders-search"
              />
            </Stack>

            {error && (
              <Alert
                severity="error"
                action={
                  <Button color="inherit" onClick={update}>
                    Retry
                  </Button>
                }
                className="orders-error"
              >
                {error}
              </Alert>
            )}
            <DataGrid<Order>
              rows={rows}
              columns={columns}
              loading={loading && orders === null}
              paginationMode="server"
              paginationModel={{
                page: offset / PAGE_SIZE,
                pageSize: PAGE_SIZE,
              }}
              onPaginationModelChange={({ page }) =>
                setOffset(page * PAGE_SIZE)
              }
              rowCount={-1}
              paginationMeta={{
                hasNextPage: (orders?.length ?? 0) > PAGE_SIZE,
              }}
              pageSizeOptions={[PAGE_SIZE]}
              disableRowSelectionOnClick
              localeText={{
                noRowsLabel: query ? 'No matching orders' : 'No orders found',
              }}
              className="orders-grid"
            />
          </Paper>
          <Typography
            variant="caption"
            color="text.secondary"
            className="search-note"
          >
            Search is limited to the current page.
          </Typography>
        </Box>
      </Box>
    </ThemeProvider>
  )
}

function formatDate(value: string) {
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
