import { useState } from 'react'

import type { HealthStatus, SessionInfoStatus, SessionStatus } from '../../app/types'
import styles from '../panels.module.css'

type SessionPanelProps = {
  sessionId: string
  sessionStatus: SessionStatus
  sessionError: string | null
  sessionInfoStatus: SessionInfoStatus
  sessionInfoError: string | null
  sessionFilesCount: number | null
  sessionBundlesCount: number | null
  llmProvider: string | null
  healthStatus: HealthStatus
  onCreateSession: () => void
  onLoadSession: (value: string) => void | Promise<void>
  onNext: () => void
}

const statusLabels: Record<SessionStatus, string> = {
  idle: 'Not Started',
  creating: 'Creating',
  loading: 'Loading',
  ready: 'Ready',
  error: 'Needs Attention',
}

export function SessionPanel({
  sessionId,
  sessionStatus,
  sessionError,
  sessionInfoStatus,
  sessionInfoError,
  sessionFilesCount,
  sessionBundlesCount,
  llmProvider,
  healthStatus,
  onCreateSession,
  onLoadSession,
  onNext,
}: SessionPanelProps) {
  const [inputSessionId, setInputSessionId] = useState('')

  const isBusy = sessionStatus === 'creating' || sessionStatus === 'loading'
  const hasFiles = (sessionFilesCount ?? 0) > 0
  const filesLabel =
    sessionInfoStatus === 'loading'
      ? 'Checking uploads...'
      : sessionFilesCount === null
      ? 'Uploaded files: --'
      : `Uploaded files: ${sessionFilesCount}`
  const bundlesLabel =
    sessionBundlesCount === null ? 'Bundles: --' : `Bundles: ${sessionBundlesCount}`
  const canContinue = Boolean(sessionId)

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
            {hasFiles ? 'Uploads Ready' : 'Awaiting Upload'}
          </span>
          <p className={styles.panelMeta}>{filesLabel}</p>
          <p className={styles.panelMeta}>{bundlesLabel}</p>
          {sessionInfoError ? (
            <p className={styles.errorText}>{sessionInfoError}</p>
          ) : null}
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
      <div className={styles.panel}>
        <h2 className={styles.panelTitle}>Workflow Navigation</h2>
        <div className={styles.buttonRow}>
          <button
            className={styles.buttonPrimary}
            type="button"
            onClick={onNext}
            disabled={!canContinue}
            aria-label="Continue to upload step"
          >
            Continue to Upload
          </button>
        </div>
      </div>
    </section>
  )
}
