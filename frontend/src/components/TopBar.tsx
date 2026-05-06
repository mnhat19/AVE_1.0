import type { HealthStatus } from '../app/types'
import styles from './TopBar.module.css'

type TopBarProps = {
  sessionId: string
  healthStatus: HealthStatus
  apiBaseUrl: string
  mockMode: boolean
}

const healthLabels: Record<HealthStatus, string> = {
  ok: 'Operational',
  warn: 'Attention',
  unknown: 'Offline',
}

function TopBar({ sessionId, healthStatus, apiBaseUrl, mockMode }: TopBarProps) {
  const healthClass =
    healthStatus === 'ok'
      ? styles.healthOk
      : healthStatus === 'warn'
      ? styles.healthWarn
      : ''

  const handleCopy = async () => {
    if (!sessionId) {
      return
    }

    try {
      await navigator.clipboard.writeText(sessionId)
    } catch {
      // Ignore clipboard errors to avoid blocking primary flow.
    }
  }

  return (
    <div className={styles.topBar}>
      <div className={styles.brand}>
        <span className={styles.brandTitle}>AuditControl AI</span>
        <nav className={styles.nav} aria-label="Primary">
          <a className={`${styles.navLink} ${styles.navLinkActive}`} href="#">
            Dashboard
          </a>
          <a className={styles.navLink} href="#">
            Logs
          </a>
          <a className={styles.navLink} href="#">
            Reports
          </a>
        </nav>
      </div>
      <div className={styles.statusGroup}>
        <div className={styles.baseUrl} title={apiBaseUrl}>
          {apiBaseUrl} {mockMode && <span className={styles.healthWarn}>(Mock Mode)</span>}
        </div>
        <div className={`${styles.health} ${healthClass}`}>
          <span className={styles.healthDot} aria-hidden="true" />
          {healthLabels[healthStatus]}
        </div>
        <div className={styles.session}>
          <span className={styles.sessionLabel}>Session</span>
          <span className={styles.sessionValue}>{sessionId || '--'}</span>
          <button
            className={styles.copyButton}
            type="button"
            aria-label="Copy session id"
            disabled={!sessionId}
            onClick={handleCopy}
          >
            Copy
          </button>
        </div>
      </div>
    </div>
  )
}

export default TopBar
