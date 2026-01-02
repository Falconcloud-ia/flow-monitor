import { useState, useEffect, useCallback, useRef } from 'react'

// ═══════════════════════════════════════════════════════════════════════════════
// API Configuration
// ═══════════════════════════════════════════════════════════════════════════════

const API_BASE_URL = 'http://localhost:8001'

// ═══════════════════════════════════════════════════════════════════════════════
// Custom Hook: Dashboard Data
// ═══════════════════════════════════════════════════════════════════════════════

function useDashboardData() {
  const [data, setData] = useState({
    readings: [],
    alerts: [],
    stats: {
      total_readings: 0,
      readings_by_risk: { LOW: 0, MEDIUM: 0, HIGH: 0, CRITICAL: 0 },
      alerts_sent: 0,
      uptime_seconds: 0
    }
  })
  const [connected, setConnected] = useState(false)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const eventSourceRef = useRef(null)

  // Fetch initial data
  const fetchData = useCallback(async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/api/dashboard/data`)
      if (!response.ok) throw new Error('Failed to fetch data')
      const result = await response.json()
      setData(result)
      setConnected(true)
      setLoading(false)
    } catch (err) {
      setError(err.message)
      setConnected(false)
      setLoading(false)
    }
  }, [])

  // Setup SSE connection
  useEffect(() => {
    fetchData()

    // Connect to SSE stream
    const eventSource = new EventSource(`${API_BASE_URL}/api/dashboard/stream`)
    eventSourceRef.current = eventSource

    eventSource.addEventListener('connected', () => {
      setConnected(true)
      console.log('📡 SSE Connected')
    })

    eventSource.addEventListener('reading', (event) => {
      const reading = JSON.parse(event.data)
      setData(prev => ({
        ...prev,
        readings: [...prev.readings.slice(-99), reading],
        stats: {
          ...prev.stats,
          total_readings: prev.stats.total_readings + 1,
          readings_by_risk: {
            ...prev.stats.readings_by_risk,
            [reading.risk_level]: (prev.stats.readings_by_risk[reading.risk_level] || 0) + 1
          }
        }
      }))
    })

    eventSource.addEventListener('heartbeat', () => {
      setConnected(true)
    })

    eventSource.onerror = () => {
      setConnected(false)
      // Retry connection after 5 seconds
      setTimeout(() => {
        eventSource.close()
        fetchData()
      }, 5000)
    }

    // Polling fallback for alerts
    const alertsInterval = setInterval(async () => {
      try {
        const response = await fetch(`${API_BASE_URL}/api/dashboard/alerts?limit=20`)
        if (response.ok) {
          const result = await response.json()
          setData(prev => ({ ...prev, alerts: result.alerts }))
        }
      } catch { }
    }, 3000)

    return () => {
      eventSource.close()
      clearInterval(alertsInterval)
    }
  }, [fetchData])

  return { data, connected, loading, error, refetch: fetchData }
}

// ═══════════════════════════════════════════════════════════════════════════════
// Sidebar Component
// ═══════════════════════════════════════════════════════════════════════════════

function Sidebar({ connected }) {
  const navItems = [
    { icon: '📊', label: 'Dashboard', active: true },
    { icon: '🌡️', label: 'Sensores', active: false },
    { icon: '🔔', label: 'Alertas', active: false },
    { icon: '📈', label: 'Analítica', active: false },
    { icon: '⚙️', label: 'Configuración', active: false },
  ]

  return (
    <aside className="sidebar">
      <div className="sidebar-header">
        <div className="sidebar-logo">
          <div className="sidebar-logo-icon">🔥</div>
          <div className="sidebar-logo-text">
            <span className="sidebar-logo-title">Flow-Monitor</span>
            <span className="sidebar-logo-subtitle">Industrial IoT</span>
          </div>
        </div>
      </div>

      <nav className="sidebar-nav">
        {navItems.map((item, index) => (
          <div
            key={index}
            className={`nav-item ${item.active ? 'active' : ''}`}
          >
            <span className="nav-icon">{item.icon}</span>
            <span>{item.label}</span>
          </div>
        ))}
      </nav>

      <div className="sidebar-footer">
        <div className={`status-card ${connected ? '' : 'disconnected'}`}>
          <div className="status-indicator-dot"></div>
          <div className="status-text">
            <div className="status-label">Estado del Sistema</div>
            <div className="status-value">
              {connected ? 'Operativo' : 'Desconectado'}
            </div>
          </div>
        </div>
      </div>
    </aside>
  )
}

// ═══════════════════════════════════════════════════════════════════════════════
// Stat Card Component
// ═══════════════════════════════════════════════════════════════════════════════

function StatCard({ label, value, icon, riskLevel, isCritical, trend }) {
  return (
    <div className={`stat-card ${isCritical ? 'critical' : ''}`}>
      <div className="stat-card-header">
        <span className="stat-card-label">{label}</span>
        <div className="stat-card-icon">{icon}</div>
      </div>
      <div className={`stat-card-value ${riskLevel?.toLowerCase() || ''}`}>
        {typeof value === 'number' ? value.toLocaleString() : value}
      </div>
      {trend && (
        <div className={`stat-card-trend ${trend > 0 ? 'trend-up' : 'trend-down'}`}>
          {trend > 0 ? '↑' : '↓'} {Math.abs(trend)}% vs anterior
        </div>
      )}
    </div>
  )
}

// ═══════════════════════════════════════════════════════════════════════════════
// Temperature Gauge Component
// ═══════════════════════════════════════════════════════════════════════════════

function TemperatureGauge({ value, maxValue = 120, riskLevel }) {
  const percentage = Math.min((value / maxValue) * 100, 100)
  const circumference = 2 * Math.PI * 80 // radius = 80
  const strokeDashoffset = circumference - (percentage / 100) * circumference * 0.75 // 270 degrees

  return (
    <div className="gauge-container">
      <div className="gauge">
        <svg width="200" height="200" viewBox="0 0 200 200">
          {/* Background arc */}
          <circle
            cx="100"
            cy="100"
            r="80"
            className="gauge-bg"
            strokeDasharray={`${circumference * 0.75} ${circumference * 0.25}`}
            transform="rotate(135 100 100)"
          />
          {/* Value arc */}
          <circle
            cx="100"
            cy="100"
            r="80"
            className={`gauge-fill ${riskLevel?.toLowerCase() || 'low'}`}
            strokeDasharray={circumference}
            strokeDashoffset={strokeDashoffset}
            transform="rotate(135 100 100)"
          />
        </svg>
        <div className="gauge-center">
          <div className="gauge-value">{value?.toFixed(1) || '0.0'}</div>
          <div className="gauge-unit">°C</div>
        </div>
      </div>
      <div className="gauge-label">Temperatura Actual</div>
    </div>
  )
}

// ═══════════════════════════════════════════════════════════════════════════════
// Temperature Chart Component
// ═══════════════════════════════════════════════════════════════════════════════

function TemperatureChart({ readings }) {
  const maxValue = 120 // Max temp for scaling
  const chartData = readings.slice(-60)

  if (chartData.length === 0) {
    return (
      <div className="temperature-chart">
        <div className="empty-state">
          <div className="empty-state-icon">📊</div>
          <p>Esperando datos del sensor...</p>
        </div>
      </div>
    )
  }

  return (
    <div className="temperature-chart">
      {chartData.map((reading, index) => {
        const height = Math.min((reading.value / maxValue) * 100, 100)
        return (
          <div
            key={reading.id || index}
            className={`chart-bar ${reading.risk_level.toLowerCase()}`}
            style={{ height: `${height}%` }}
            title={`${reading.value.toFixed(1)}${reading.unit} - ${reading.risk_level}`}
          />
        )
      })}
    </div>
  )
}

// ═══════════════════════════════════════════════════════════════════════════════
// Alerts List Component
// ═══════════════════════════════════════════════════════════════════════════════

function AlertsList({ alerts }) {
  if (alerts.length === 0) {
    return (
      <div className="empty-state">
        <div className="empty-state-icon">🔔</div>
        <p>Sin alertas activas</p>
      </div>
    )
  }

  return (
    <div className="alerts-list">
      {alerts.slice().reverse().slice(0, 10).map((alert) => (
        <div key={alert.id} className={`alert-item ${alert.risk_level.toLowerCase()}`}>
          <div className="alert-header">
            <span className="alert-sensor">
              <span className="alert-sensor-icon">🔥</span>
              {alert.sensor_id}
            </span>
            <span className="alert-time">
              {new Date(alert.timestamp).toLocaleTimeString('es-CL')}
            </span>
          </div>
          <p className="alert-message">{alert.message?.substring(0, 80)}...</p>
          <span className={`alert-badge ${alert.channel}`}>
            {alert.channel === 'whatsapp' ? '📱' : '📧'} {alert.channel}
          </span>
        </div>
      ))}
    </div>
  )
}

// ═══════════════════════════════════════════════════════════════════════════════
// Readings Table Component
// ═══════════════════════════════════════════════════════════════════════════════

function ReadingsTable({ readings }) {
  const displayReadings = readings.slice(-8).reverse()

  if (displayReadings.length === 0) {
    return (
      <div className="empty-state">
        <div className="empty-state-icon">📈</div>
        <p>Sin lecturas registradas</p>
      </div>
    )
  }

  return (
    <table className="readings-table">
      <thead>
        <tr>
          <th>Sensor</th>
          <th>Valor</th>
          <th>Ubicación</th>
          <th>Riesgo</th>
          <th>Prob. Fallo</th>
          <th>Hora</th>
        </tr>
      </thead>
      <tbody>
        {displayReadings.map((reading) => {
          const probability = reading.prediction?.failure_probability || 0
          const probColor = probability > 0.7 ? 'var(--color-risk-critical)' :
            probability > 0.4 ? 'var(--color-risk-high)' :
              probability > 0.2 ? 'var(--color-risk-medium)' :
                'var(--color-risk-low)'

          return (
            <tr key={reading.id} className={reading.risk_level.toLowerCase()}>
              <td>
                <span style={{ fontWeight: 600 }}>{reading.sensor_id}</span>
              </td>
              <td>
                <span className="reading-value">
                  {reading.value.toFixed(1)}{reading.unit}
                </span>
              </td>
              <td>
                <span className="reading-location">{reading.location}</span>
              </td>
              <td>
                <span className={`risk-badge ${reading.risk_level.toLowerCase()}`}>
                  {reading.risk_emoji} {reading.risk_level}
                </span>
              </td>
              <td>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <div className="probability-bar">
                    <div
                      className="probability-fill"
                      style={{
                        width: `${probability * 100}%`,
                        background: probColor
                      }}
                    />
                  </div>
                  <span style={{ fontFamily: 'var(--font-mono)', fontSize: '0.75rem' }}>
                    {(probability * 100).toFixed(0)}%
                  </span>
                </div>
              </td>
              <td style={{ color: 'var(--color-text-muted)', fontFamily: 'var(--font-mono)' }}>
                {new Date(reading.timestamp).toLocaleTimeString('es-CL')}
              </td>
            </tr>
          )
        })}
      </tbody>
    </table>
  )
}

// ═══════════════════════════════════════════════════════════════════════════════
// Main App Component
// ═══════════════════════════════════════════════════════════════════════════════

function App() {
  const { data, connected, loading } = useDashboardData()
  const hasCritical = data.stats.readings_by_risk.CRITICAL > 0

  // Get current temperature from latest reading
  const latestReading = data.readings[data.readings.length - 1]
  const currentTemp = latestReading?.value || 0
  const currentRisk = latestReading?.risk_level || 'LOW'

  if (loading) {
    return (
      <div className="dashboard" style={{ display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
        <div className="loading">
          <div className="loading-spinner"></div>
          <p className="loading-text">Conectando al servidor...</p>
        </div>
      </div>
    )
  }

  return (
    <div className="dashboard">
      {/* Sidebar */}
      <Sidebar connected={connected} />

      {/* Main Content */}
      <div className="main-content">
        {/* Header */}
        <header className="dashboard-header">
          <div className="header-title">
            <h2>Panel de Monitoreo</h2>
            <span>Monitoreo en tiempo real de sensores industriales</span>
          </div>
          <div className="header-actions">
            <div className="header-stat">
              <span className="header-stat-icon">⏱️</span>
              <span>Uptime: {Math.floor(data.stats.uptime_seconds / 60)}m</span>
            </div>
            <div className="header-stat">
              <span className="header-stat-icon">📡</span>
              <span>{data.stats.total_readings} lecturas</span>
            </div>
          </div>
        </header>

        {/* Main Grid */}
        <main className="dashboard-main">
          {/* Stats Cards Row */}
          <div className="stats-grid">
            <StatCard
              label="Total Lecturas"
              value={data.stats.total_readings}
              icon="📊"
            />
            <StatCard
              label="Nivel Bajo"
              value={data.stats.readings_by_risk.LOW}
              icon="🟢"
              riskLevel="low"
            />
            <StatCard
              label="Nivel Alto"
              value={data.stats.readings_by_risk.HIGH}
              icon="🟠"
              riskLevel="high"
            />
            <StatCard
              label="Críticos"
              value={data.stats.readings_by_risk.CRITICAL}
              icon="🔴"
              riskLevel="critical"
              isCritical={hasCritical}
            />
          </div>

          {/* Chart Section */}
          <section className="chart-section">
            <div className="section-header">
              <h2 className="section-title">
                <span className="section-title-icon">📈</span>
                <span>Temperatura en Tiempo Real</span>
              </h2>
              <div className="section-actions">
                <button className="btn-icon" title="Actualizar">🔄</button>
                <button className="btn-icon" title="Expandir">⛶</button>
              </div>
            </div>
            <div className="chart-container">
              <TemperatureChart readings={data.readings} />
            </div>
          </section>

          {/* Alerts Panel */}
          <section className="alerts-section">
            <div className="section-header">
              <h2 className="section-title">
                <span className="section-title-icon">🔔</span>
                <span>Alertas ({data.stats.alerts_sent})</span>
              </h2>
            </div>
            <AlertsList alerts={data.alerts} />
          </section>

          {/* Readings Table */}
          <section className="readings-section">
            <div className="section-header">
              <h2 className="section-title">
                <span className="section-title-icon">📋</span>
                <span>Últimas Lecturas</span>
              </h2>
            </div>
            <ReadingsTable readings={data.readings} />
          </section>
        </main>
      </div>
    </div>
  )
}

export default App
