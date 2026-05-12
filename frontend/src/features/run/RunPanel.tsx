import type { RunResponse } from '../../services/api'
import type { RunStage, RunStatus, SessionInfoStatus } from '../../app/types'
import styles from '../panels.module.css'

type RunPanelProps = {
  sessionId: string
  sessionFilesCount: number | null
  sessionInfoStatus: SessionInfoStatus
  runStage: RunStage
  runStatus: RunStatus
  runError: string | null
  runResult: RunResponse | null
  onStageChange: (stage: RunStage) => void
  onRun: (stage: RunStage) => void
  onBack: () => void
  onNext: () => void
}

const stageOptions: RunStage[] = ['INTERIM', 'FIELDWORK', 'BOTH']

const statusLabels: Record<RunStatus, string> = {
  idle: 'Idle',
  running: 'Running',
  success: 'Completed',
  error: 'Needs Attention',
}

export function RunPanel({
  sessionId,
  sessionFilesCount,
  sessionInfoStatus,
  runStage,
  runStatus,
  runError,
  runResult,
  onStageChange,
  onRun,
  onBack,
  onNext,
}: RunPanelProps) {
  const hasFiles = (sessionFilesCount ?? 0) > 0
  const canRun = Boolean(sessionId) && runStatus !== 'running' && hasFiles
  const tasks = Array.isArray(runResult?.audit_tasks)
    ? runResult?.audit_tasks
    : []
  const statusMessage = !sessionId
    ? 'Create or load a session before running.'
    : sessionInfoStatus === 'loading'
    ? 'Checking uploads for this session.'
    : hasFiles
    ? 'Session ready for execution.'
    : 'No uploaded files detected for this session.'
  const filesLabel =
    sessionFilesCount === null ? 'Uploaded files: --' : `Uploaded files: ${sessionFilesCount}`
  const canContinue = runStatus === 'success'

  return (
    <section className={styles.section}>
      <div className={styles.grid}>
        <div className={styles.panel}>
          <h2 className={styles.panelTitle}>Execution Controls</h2>
          <p className={styles.panelMeta}>
            Select the audit stage and launch the multi-agent workflow.
          </p>
          <div className={styles.buttonRow}>
            {stageOptions.map((stage) => (
              <button
                key={stage}
                className={
                  stage === runStage
                    ? styles.buttonToggleActive
                    : styles.buttonGhost
                }
                type="button"
                onClick={() => onStageChange(stage)}
                disabled={runStatus === 'running'}
                aria-pressed={stage === runStage}
                aria-label={`Select stage ${stage}`}
              >
                {stage}
              </button>
            ))}
            <button
              className={styles.buttonPrimary}
              type="button"
              onClick={() => onRun(runStage)}
              disabled={!canRun}
              aria-label="Run Audit with selected stage"
              aria-busy={runStatus === 'running'}
            >
              {runStatus === 'running' ? 'Running...' : 'Run Audit'}
            </button>
          </div>
        </div>
        <div className={styles.panel}>
          <h2 className={styles.panelTitle}>Execution Status</h2>
          <p className={styles.panelMeta}>{statusMessage}</p>
          <p className={styles.panelMeta}>{filesLabel}</p>
          <span className={styles.badge}>{statusLabels[runStatus]}</span>
          {runError ? <p className={styles.errorText}>{runError}</p> : null}
        </div>
      </div>
      <div className={styles.panel}>
        <h2 className={styles.panelTitle}>Execution Plan</h2>
        {tasks.length ? (
          <table className={styles.table}>
            <thead>
              <tr>
                <th>Task</th>
                <th>Agent</th>
                <th>Priority</th>
                <th>Status</th>
              </tr>
            </thead>
            <tbody>
              {tasks.map((task, index) => {
                const t = task as Record<string, unknown>
                return (
                  <tr key={`task-${index}`}>
                    <td>{String(t?.name ?? 'Task')}</td>
                    <td>{String(t?.agent ?? 'Agent')}</td>
                    <td>{String(t?.priority ?? 'Medium')}</td>
                    <td>{String(t?.status ?? 'Queued')}</td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        ) : (
          <p className={styles.panelMeta}>Execution plan will appear after a run.</p>
        )}
      </div>
      <div className={styles.panel}>
        <h2 className={styles.panelTitle}>Workflow Navigation</h2>
        <div className={styles.buttonRow}>
          <button
            className={styles.buttonGhost}
            type="button"
            onClick={onBack}
            aria-label="Back to upload step"
          >
            Back to Upload
          </button>
          <button
            className={styles.buttonPrimary}
            type="button"
            onClick={onNext}
            disabled={!canContinue}
            aria-label="Continue to results step"
          >
            Continue to Results
          </button>
        </div>
      </div>
    </section>
  )
}
