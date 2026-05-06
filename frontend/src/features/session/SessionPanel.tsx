import { useState } from 'react'

import type { HealthStatus, SessionStatus } from '../../app/types'
import styles from '../panels.module.css'

type SessionPanelProps = {
  sessionId: string
  sessionStatus: SessionStatus
  sessionError: string | null
  llmProvider: string | null
  healthStatus: HealthStatus
  onCreateSession: () => void
  onLoadSession: (value: string) => void
}

const statusLabels: Record<SessionStatus, string> = {
  idle: 'Not Started',
  creating: 'Creating',
  ready: 'Ready',
  error: 'Needs Attention',
}

export function SessionPanel({
  sessionId,
  sessionStatus,
  sessionError,
  llmProvider,
  healthStatus,
  onCreateSession,
  onLoadSession,
}: SessionPanelProps) {
  const [inputSessionId, setInputSessionId] = useState('')

  const isBusy = sessionStatus === 'creating'

  return (
    <section className={styles.section}>
      <div className={styles.grid}>
        <div className={styles.panel}>
          <h2 className={styles.panelTitle}>Session Initialization</h2>
          <p className={styles.panelMeta}>
            Create a new audit session to anchor uploads, tasks, and outputs.
          </p>
          <div className={styles.inputRow}>
            <label className={styles.label} htmlFor="existing-session">
              Existing Session ID
            </label>
            <input
              id="existing-session"
              className={styles.input}
              value={inputSessionId}
              onChange={(event) => setInputSessionId(event.target.value)}
              placeholder="Enter session id"
            />
          </div>
          <div className={styles.buttonRow}>
            <button
              className={styles.buttonPrimary}
              type="button"
              onClick={onCreateSession}
              disabled={isBusy}
              aria-label="Create a new session"
              aria-busy={isBusy}
            >
              Create Session
            </button>
            <button
              className={styles.buttonGhost}
              type="button"
              onClick={() => onLoadSession(inputSessionId)}
              disabled={isBusy}
              aria-label="Load existing session"
            >
              Load Existing
            </button>
          </div>
          {sessionError ? (
            <p className={styles.errorText}>{sessionError}</p>
          ) : null}
        </div>
        <div className={styles.panel}>
          <h2 className={styles.panelTitle}>Checklist Snapshot</h2>
          <p className={styles.panelMeta}>
            Verify required document groups before executing the audit pipeline.
          </p>
          <span className={`${styles.badge} ${styles.badgeNeutral}`}>
            Awaiting Upload
          </span>
        </div>
      </div>
      <div className={styles.panel}>
        <h2 className={styles.panelTitle}>Session Metadata</h2>
        <table className={styles.table}>
          <tbody>
            <tr>
              <td>Session ID</td>
              <td>{sessionId || '--'}</td>
            </tr>
            <tr>
              <td>LLM Provider</td>
              <td>{llmProvider ?? '--'}</td>
            </tr>
            <tr>
              <td>API Health</td>
              <td>{healthStatus.toUpperCase()}</td>
            </tr>
            <tr>
              <td>Session Status</td>
              <td>{statusLabels[sessionStatus]}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </section>
  )
}
