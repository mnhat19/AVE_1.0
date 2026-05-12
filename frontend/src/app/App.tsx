import { useCallback, useEffect, useMemo, useState } from 'react'

import StepHeader from '../components/StepHeader'
import { ResultsPanel } from '../features/results/ResultsPanel'
import { RunPanel } from '../features/run/RunPanel'
import { SessionPanel } from '../features/session/SessionPanel'
import { UploadPanel } from '../features/upload/UploadPanel'
import {
  API_BASE_URL,
  createSession,
  getErrorMessage,
  getHealth,
  getSessionSummary,
  MOCK_MODE,
  runSession,
  type RunResponse,
  type SessionSummaryResponse,
} from '../services/api'
import AppShell from './AppShell'
import type {
  HealthStatus,
  RunStage,
  RunStatus,
  SessionStatus,
  SessionInfoStatus,
  StepDefinition,
  StepKey,
} from './types'

const SESSION_STORAGE_KEY = 'ave.sessionId'

const steps: StepDefinition[] = [
  {
    key: 'session',
    label: 'Session',
    title: 'Start Session',
    description:
      'Initialize a secure audit workspace and capture the session metadata.',
  },
  {
    key: 'upload',
    label: 'Upload',
    title: 'Source Upload',
    description:
      'Drop source documents and confirm validation before running the pipeline.',
  },
  {
    key: 'run',
    label: 'Run',
    title: 'Audit Engine',
    description:
      'Select the audit stage and execute the agent workflow safely.',
  },
  {
    key: 'results',
    label: 'Results',
    title: 'Analysis Results',
    description:
      'Review findings, download outputs, and provide analyst feedback.',
  },
]

function App() {
  const [sessionId, setSessionId] = useState(() => {
    if (typeof window === 'undefined') {
      return ''
    }

    return localStorage.getItem(SESSION_STORAGE_KEY) ?? ''
  })
  const [sessionStatus, setSessionStatus] = useState<SessionStatus>(
    sessionId ? 'ready' : 'idle'
  )
  const [sessionError, setSessionError] = useState<string | null>(null)
  const [sessionInfoStatus, setSessionInfoStatus] = useState<SessionInfoStatus>('idle')
  const [sessionInfoError, setSessionInfoError] = useState<string | null>(null)
  const [sessionFilesCount, setSessionFilesCount] = useState<number | null>(null)
  const [sessionBundlesCount, setSessionBundlesCount] = useState<number | null>(null)
  const [healthStatus, setHealthStatus] = useState<HealthStatus>('unknown')
  const [llmProvider, setLlmProvider] = useState<string | null>(null)
  const [runStage, setRunStage] = useState<RunStage>('BOTH')
  const [runStatus, setRunStatus] = useState<RunStatus>('idle')
  const [runError, setRunError] = useState<string | null>(null)
  const [runResult, setRunResult] = useState<RunResponse | null>(null)
  const [activeStep, setActiveStep] = useState<StepKey>('session')

  const activeDefinition = useMemo(
    () => steps.find((step) => step.key === activeStep) ?? steps[0],
    [activeStep]
  )

  useEffect(() => {
    let isActive = true

    getHealth()
      .then((data) => {
        if (!isActive) {
          return
        }

        setHealthStatus(data.status === 'ok' ? 'ok' : 'warn')
        setLlmProvider(data.llm_provider ?? null)
      })
      .catch(() => {
        if (!isActive) {
          return
        }

        setHealthStatus('warn')
        setLlmProvider(null)
      })

    return () => {
      isActive = false
    }
  }, [])

  useEffect(() => {
    if (typeof window === 'undefined') {
      return
    }

    if (sessionId) {
      localStorage.setItem(SESSION_STORAGE_KEY, sessionId)
      return
    }

    localStorage.removeItem(SESSION_STORAGE_KEY)
  }, [sessionId])

  const resetSessionInfo = useCallback(() => {
    setSessionInfoStatus('idle')
    setSessionInfoError(null)
    setSessionFilesCount(null)
    setSessionBundlesCount(null)
  }, [])

  const applySessionSummary = useCallback((summary: SessionSummaryResponse) => {
    setSessionFilesCount(summary.files_count)
    setSessionBundlesCount(summary.bundles_count)
    setSessionInfoStatus('success')
    setSessionInfoError(null)
  }, [])

  const refreshSessionSummary = useCallback(async (value: string) => {
    if (!value) {
      resetSessionInfo()
      return null
    }

    setSessionInfoStatus('loading')
    setSessionInfoError(null)

    try {
      const summary = await getSessionSummary(value)
      applySessionSummary(summary)
      return summary
    } catch (error) {
      setSessionInfoStatus('error')
      setSessionInfoError(getErrorMessage(error, 'Unable to load session details.'))
      return null
    }
  }, [applySessionSummary, resetSessionInfo])

  useEffect(() => {
    let isActive = true

    const validate = async () => {
      if (!sessionId) {
        resetSessionInfo()
        return
      }

      const summary = await refreshSessionSummary(sessionId)
      if (!isActive) {
        return
      }
      if (!summary) {
        setSessionStatus('error')
        setSessionError('Unable to load session details.')
      }
    }

    void validate()

    return () => {
      isActive = false
    }
  }, [refreshSessionSummary, resetSessionInfo, sessionId])

  const handleCreateSession = async () => {
    setSessionError(null)
    setSessionStatus('creating')
    setRunStatus('idle')
    setRunResult(null)
    setRunError(null)

    try {
      const response = await createSession()
      setSessionId(response.session_id)
      setSessionStatus('ready')
      setSessionFilesCount(0)
      setSessionBundlesCount(0)
      setSessionInfoStatus('success')
      setActiveStep('upload')
    } catch (error) {
      setSessionStatus('error')
      setSessionError(getErrorMessage(error, 'Unable to create a session.'))
    }
  }

  const loadExistingSession = async (value: string) => {
    const trimmed = value.trim()
    if (!trimmed) {
      setSessionStatus('error')
      setSessionError('Session ID is required before loading.')
      return
    }

    setSessionError(null)
    setSessionStatus('loading')
    setRunStatus('idle')
    setRunResult(null)
    setRunError(null)

    try {
      const summary = await refreshSessionSummary(trimmed)
      if (!summary) {
        setSessionStatus('error')
        setSessionError('Unable to load session details.')
        return
      }
      setSessionId(trimmed)
      setSessionStatus('ready')
      setActiveStep('upload')
    } catch (error) {
      setSessionStatus('error')
      setSessionError(getErrorMessage(error, 'Unable to load session.'))
    }
  }

  const handleLoadSession = (value: string) => {
    void loadExistingSession(value)
  }

  const handleQueueChange = (count: number) => {
    setSessionFilesCount(count)
    setSessionInfoError(null)
    if (sessionInfoStatus !== 'loading') {
      setSessionInfoStatus('success')
    }
  }

  const resolveFilesCount = async () => {
    if (sessionFilesCount !== null) {
      return sessionFilesCount
    }

    const summary = await refreshSessionSummary(sessionId)
    return summary?.files_count ?? 0
  }

  const handleRun = async (stage: RunStage) => {
    if (!sessionId) {
      setRunStatus('error')
      setRunError('Session ID is required before running the audit.')
      return
    }

    const filesCount = await resolveFilesCount()
    if (!filesCount) {
      setRunStatus('error')
      setRunError('No files found for this session. Upload documents first.')
      return
    }

    setRunError(null)
    setRunStatus('running')
    setRunStage(stage)

    try {
      const response = await runSession(sessionId, stage)
      setRunResult(response)
      setRunStatus('success')
      setActiveStep('results')
    } catch (error) {
      setRunStatus('error')
      setRunError(getErrorMessage(error, 'Run failed.'))
    }
  }

  return (
    <AppShell
      steps={steps}
      activeStep={activeStep}
      onStepChange={setActiveStep}
      sessionId={sessionId}
      healthStatus={healthStatus}
      apiBaseUrl={API_BASE_URL}
      mockMode={MOCK_MODE}
    >
      <StepHeader
        steps={steps}
        activeStep={activeDefinition.key}
        title={activeDefinition.title}
        description={activeDefinition.description}
      />
      {activeStep === 'session' ? (
        <SessionPanel
          sessionId={sessionId}
          sessionStatus={sessionStatus}
          sessionError={sessionError}
          sessionInfoStatus={sessionInfoStatus}
          sessionInfoError={sessionInfoError}
          sessionFilesCount={sessionFilesCount}
          sessionBundlesCount={sessionBundlesCount}
          llmProvider={llmProvider}
          healthStatus={healthStatus}
          onCreateSession={handleCreateSession}
          onLoadSession={handleLoadSession}
          onNext={() => setActiveStep('upload')}
        />
      ) : null}
      {activeStep === 'upload' ? (
        <UploadPanel
          sessionId={sessionId}
          onQueueChange={handleQueueChange}
          onBack={() => setActiveStep('session')}
          onNext={() => setActiveStep('run')}
        />
      ) : null}
      {activeStep === 'run' ? (
        <RunPanel
          sessionId={sessionId}
          sessionFilesCount={sessionFilesCount}
          sessionInfoStatus={sessionInfoStatus}
          runStage={runStage}
          runStatus={runStatus}
          runError={runError}
          runResult={runResult}
          onStageChange={setRunStage}
          onRun={handleRun}
          onBack={() => setActiveStep('upload')}
          onNext={() => setActiveStep('results')}
        />
      ) : null}
      {activeStep === 'results' ? (
        <ResultsPanel
          sessionId={sessionId}
          runStatus={runStatus}
          runError={runError}
          runResult={runResult}
          onBack={() => setActiveStep('run')}
        />
      ) : null}
    </AppShell>
  )
}

export default App
