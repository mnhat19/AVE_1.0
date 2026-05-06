import { useCallback, useEffect, useMemo, useState } from 'react'

import {
  API_BASE_URL,
  getErrorMessage,
  getFindings,
  submitFeedback,
  type FeedbackAction,
  type Finding,
  type RunResponse,
} from '../../services/api'
import type { RunStatus } from '../../app/types'
import styles from '../panels.module.css'

type ResultsPanelProps = {
  sessionId: string
  runStatus: RunStatus
  runError: string | null
  runResult: RunResponse | null
}

export function ResultsPanel({
  sessionId,
  runStatus,
  runError,
  runResult,
}: ResultsPanelProps) {
  const [findings, setFindings] = useState<Finding[]>([])
  const [findingsStatus, setFindingsStatus] = useState<'idle' | 'loading' | 'error' | 'success'>(
    'idle'
  )
  const [findingsError, setFindingsError] = useState<string | null>(null)
  const [severityFilter, setSeverityFilter] = useState('ALL')
  const [statusFilter, setStatusFilter] = useState('ALL')
  const [searchValue, setSearchValue] = useState('')
  const [selectedFinding, setSelectedFinding] = useState<Finding | null>(null)
  const [feedbackAction, setFeedbackAction] = useState<FeedbackAction>('ACCEPT')
  const [feedbackComment, setFeedbackComment] = useState('')
  const [feedbackStatus, setFeedbackStatus] = useState<'idle' | 'sending' | 'error'>(
    'idle'
  )
  const [feedbackError, setFeedbackError] = useState<string | null>(null)

  const downloads = [
    { key: 'issue_log', label: 'Issue Log (XLSX)' },
    { key: 'risk_register', label: 'Risk Register (XLSX)' },
    { key: 'memo', label: 'Audit Memo (DOCX)' },
  ]

  const canDownload = Boolean(sessionId) && Boolean(runResult)
  const changelog = runResult?.changelog ?? []
  const severityOptions = ['ALL', 'LOW', 'MEDIUM', 'HIGH', 'CRITICAL']
  const statusOptions = ['ALL', 'OPEN', 'IN_PROGRESS', 'RESOLVED', 'ESCALATED']

  const filteredFindings = useMemo(() => {
    const query = searchValue.trim().toLowerCase()
    return findings.filter((finding) => {
      const matchesSeverity =
        severityFilter === 'ALL' || finding.severity === severityFilter
      const matchesStatus =
        statusFilter === 'ALL' || finding.status === statusFilter
      const matchesQuery =
        !query ||
        finding.description.toLowerCase().includes(query) ||
        finding.id.toLowerCase().includes(query) ||
        finding.stage.toLowerCase().includes(query)

      return matchesSeverity && matchesStatus && matchesQuery
    })
  }, [findings, searchValue, severityFilter, statusFilter])

  const handleFetchFindings = useCallback(async () => {
    if (!sessionId || !runResult) {
      setFindings([])
      setFindingsStatus('idle')
      setFindingsError(null)
      return
    }

    setFindingsStatus('loading')
    setFindingsError(null)

    try {
      const data = await getFindings(sessionId)
      setFindings(data)
      setFindingsStatus('success')
    } catch (error) {
      setFindingsStatus('error')
      setFindingsError(getErrorMessage(error, 'Unable to load findings.'))
    }
  }, [sessionId, runResult])

  useEffect(() => {
    const fetchData = async () => {
      await handleFetchFindings()
    }
    void fetchData()
  }, [handleFetchFindings])

  const handleOpenFeedback = (finding: Finding) => {
    setSelectedFinding(finding)
    setFeedbackAction('ACCEPT')
    setFeedbackComment('')
    setFeedbackStatus('idle')
    setFeedbackError(null)
  }

  const handleCloseFeedback = () => {
    setSelectedFinding(null)
  }

  const handleSubmitFeedback = async () => {
    if (!selectedFinding) {
      return
    }

    setFeedbackStatus('sending')
    setFeedbackError(null)

    try {
      await submitFeedback(
        selectedFinding.id,
        feedbackAction,
        feedbackComment
      )

      const nextStatus = feedbackAction === 'MODIFY' ? 'IN_PROGRESS' : 'RESOLVED'
      setFindings((previous) =>
        previous.map((finding) =>
          finding.id === selectedFinding.id
            ? { ...finding, status: nextStatus }
            : finding
        )
      )
      setSelectedFinding(null)
      setFeedbackStatus('idle')
    } catch (error) {
      setFeedbackStatus('error')
      setFeedbackError(getErrorMessage(error, 'Unable to submit feedback.'))
    }
  }

  const severityClassMap: Record<string, string> = {
    LOW: styles.severityLow,
    MEDIUM: styles.severityMedium,
    HIGH: styles.severityHigh,
    CRITICAL: styles.severityCritical,
  }

  return (
    <section className={styles.section}>
      <div className={styles.grid}>
        <div className={styles.panel}>
          <div className={styles.kpi}>
            <span className={styles.kpiLabel}>Findings</span>
            <span className={styles.kpiValue}>
              {runResult?.findings_count ?? 0}
            </span>
          </div>
        </div>
        <div className={styles.panel}>
          <div className={styles.kpi}>
            <span className={styles.kpiLabel}>Anomalies</span>
            <span className={styles.kpiValue}>
              {runResult?.anomalies_count ?? 0}
            </span>
          </div>
        </div>
        <div className={styles.panel}>
          <div className={styles.kpi}>
            <span className={styles.kpiLabel}>Consolidated</span>
            <span className={styles.kpiValue}>
              {runResult?.consolidated_count ?? 0}
            </span>
          </div>
        </div>
      </div>
      <div className={styles.panel}>
        <h2 className={styles.panelTitle}>Findings Overview</h2>
        {runStatus === 'running' ? (
          <p className={styles.panelMeta}>
            Audit is running. Findings will populate once the run completes.
          </p>
        ) : runResult ? (
          <div className={styles.filtersRow}>
            <div className={styles.filtersGroup}>
              <input
                className={`${styles.input} ${styles.searchInput}`}
                type="search"
                placeholder="Search findings"
                value={searchValue}
                onChange={(event) => setSearchValue(event.target.value)}
              />
              <select
                className={styles.select}
                value={severityFilter}
                onChange={(event) => setSeverityFilter(event.target.value)}
              >
                {severityOptions.map((option) => (
                  <option key={option} value={option}>
                    {option}
                  </option>
                ))}
              </select>
              <select
                className={styles.select}
                value={statusFilter}
                onChange={(event) => setStatusFilter(event.target.value)}
              >
                {statusOptions.map((option) => (
                  <option key={option} value={option}>
                    {option}
                  </option>
                ))}
              </select>
            </div>
            <div className={styles.tableActions}>
              <button
                className={styles.buttonGhost}
                type="button"
                onClick={handleFetchFindings}
                disabled={findingsStatus === 'loading'}
                aria-label="Refresh findings"
                aria-busy={findingsStatus === 'loading'}
              >
                {findingsStatus === 'loading' ? 'Refreshing...' : 'Refresh'}
              </button>
            </div>
          </div>
        ) : (
          <p className={styles.panelMeta}>Run an audit to populate results.</p>
        )}
        {runError ? <p className={styles.errorText}>{runError}</p> : null}
        {runResult && findingsStatus === 'loading' ? (
          <p className={styles.panelMeta}>Loading findings...</p>
        ) : null}
        {findingsError ? <p className={styles.errorText}>{findingsError}</p> : null}
        {runResult && findingsStatus !== 'loading' ? (
          filteredFindings.length ? (
            <table className={styles.table}>
              <thead>
                <tr>
                  <th>ID</th>
                  <th>Description</th>
                  <th>Stage</th>
                  <th>Severity</th>
                  <th>Status</th>
                  <th>Confidence</th>
                  <th>Action</th>
                </tr>
              </thead>
              <tbody>
                {filteredFindings.map((finding) => (
                  <tr key={finding.id}>
                    <td>{finding.id}</td>
                    <td>{finding.description}</td>
                    <td>{finding.stage}</td>
                    <td>
                      <span
                        className={`${styles.severityBadge} ${
                          severityClassMap[finding.severity] ?? ''
                        }`}
                      >
                        {finding.severity}
                      </span>
                    </td>
                    <td>
                      <span className={styles.statusBadge}>{finding.status}</span>
                    </td>
                    <td>{(finding.confidence_score * 100).toFixed(1)}%</td>
                    <td>
                      <button
                        className={styles.buttonGhost}
                        type="button"
                        onClick={() => handleOpenFeedback(finding)}
                        aria-label={`Provide feedback for finding ${finding.id}`}
                      >
                        Feedback
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          ) : (
            <p className={styles.panelMeta}>No findings match the current filters.</p>
          )
        ) : null}
      </div>
      <div className={styles.grid}>
        <div className={styles.panel}>
          <h2 className={styles.panelTitle}>Downloads</h2>
          <ul className={styles.downloadList}>
            {downloads.map((item) => (
              <li key={item.key} className={styles.downloadItem}>
                <span>{item.label}</span>
                {canDownload ? (
                  <a
                    className={styles.buttonGhost}
                    href={`${API_BASE_URL}/api/v1/sessions/${sessionId}/download/${item.key}`}
                    aria-label={`Download ${item.label}`}
                  >
                    Download
                  </a>
                ) : (
                  <button className={styles.buttonGhost} type="button" disabled>
                    Download
                  </button>
                )}
              </li>
            ))}
          </ul>
        </div>
        <div className={styles.panel}>
          <h2 className={styles.panelTitle}>Changelog</h2>
          {changelog.length ? (
            <ul className={styles.timeline}>
              {changelog.map((entry, index) => (
                <li key={`log-${index}`} className={styles.timelineItem}>
                  {entry}
                </li>
              ))}
            </ul>
          ) : (
            <p className={styles.panelMeta}>No changelog entries yet.</p>
          )}
        </div>
      </div>
      {selectedFinding ? (
        <div className={styles.modalOverlay} role="dialog" aria-modal="true">
          <div className={styles.modal}>
            <div className={styles.modalHeader}>
              <h3 className={styles.modalTitle}>Provide Feedback</h3>
              <button
                className={styles.buttonGhost}
                type="button"
                onClick={handleCloseFeedback}
              >
                Close
              </button>
            </div>
            <div className={styles.modalBody}>
              <p className={styles.panelMeta}>{selectedFinding.description}</p>
              <div className={styles.inputRow}>
                <label className={styles.label} htmlFor="feedback-action">
                  Action
                </label>
                <select
                  id="feedback-action"
                  className={styles.select}
                  value={feedbackAction}
                  onChange={(event) =>
                    setFeedbackAction(event.target.value as FeedbackAction)
                  }
                >
                  <option value="ACCEPT">ACCEPT</option>
                  <option value="REJECT">REJECT</option>
                  <option value="MODIFY">MODIFY</option>
                </select>
              </div>
              <div className={styles.inputRow}>
                <label className={styles.label} htmlFor="feedback-comment">
                  Comment
                </label>
                <textarea
                  id="feedback-comment"
                  className={`${styles.input} ${styles.textarea}`}
                  value={feedbackComment}
                  onChange={(event) => setFeedbackComment(event.target.value)}
                  placeholder="Add supporting notes or required changes"
                />
              </div>
              {feedbackError ? (
                <p className={styles.errorText}>{feedbackError}</p>
              ) : null}
            </div>
            <div className={styles.modalFooter}>
              <button
                className={styles.buttonGhost}
                type="button"
                onClick={handleCloseFeedback}
                disabled={feedbackStatus === 'sending'}
                aria-label="Cancel feedback"
              >
                Cancel
              </button>
              <button
                className={styles.buttonPrimary}
                type="button"
                onClick={handleSubmitFeedback}
                disabled={feedbackStatus === 'sending'}
                aria-label="Submit feedback"
                aria-busy={feedbackStatus === 'sending'}
              >
                {feedbackStatus === 'sending' ? 'Submitting...' : 'Submit'}
              </button>
            </div>
          </div>
        </div>
      ) : null}
    </section>
  )
}
