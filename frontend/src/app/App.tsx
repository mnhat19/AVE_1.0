import { type ComponentType, useEffect, useMemo, useState } from 'react'

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
  MOCK_MODE,
  runSession,
  type RunResponse,
} from '../services/api'
import AppShell from './AppShell'
import type {
  HealthStatus,
  RunStage,
  RunStatus,
  SessionStatus,
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

const panels: Record<StepKey, ComponentType<any>> = {
  session: SessionPanel,
  upload: UploadPanel,
  run: RunPanel,
  results: ResultsPanel,
}

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
  const [healthStatus, setHealthStatus] = useState<HealthStatus>('unknown')
  const [llmProvider, setLlmProvider] = useState<string | null>(null)
  const [runStage, setRunStage] = useState<RunStage>('BOTH')
  const [runStatus, setRunStatus] = useState<RunStatus>('idle')
  const [runError, setRunError] = useState<string | null>(null)
  const [runResult, setRunResult] = useState<RunResponse | null>(null)
  const [activeStep, setActiveStep] = useState<StepKey>('session')

  const ActivePanel = panels[activeStep]
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
      setActiveStep('upload')
    } catch (error) {
      setSessionStatus('error')
      setSessionError(getErrorMessage(error, 'Unable to create a session.'))
    }
  }

  const handleLoadSession = (value: string) => {
    const trimmed = value.trim()
    if (!trimmed) {
      setSessionStatus('error')
      setSessionError('Session ID is required before loading.')
      return
    }

    setSessionError(null)
    setSessionId(trimmed)
    setSessionStatus('ready')
    setRunStatus('idle')
    setRunResult(null)
    setRunError(null)
    setActiveStep('upload')
  }

  const handleRun = async (stage: RunStage) => {
    if (!sessionId) {
      setRunStatus('error')
      setRunError('Session ID is required before running the audit.')
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
      <ActivePanel
        {...(activeStep === 'session'
          ? {
              sessionId,
              sessionStatus,
              sessionError,
              llmProvider,
              healthStatus,
              onCreateSession: handleCreateSession,
              onLoadSession: handleLoadSession,
            }
          : {})}
        {...(activeStep === 'upload'
          ? {
              sessionId,
            }
          : {})}
        {...(activeStep === 'run'
          ? {
              sessionId,
              runStage,
              runStatus,
              runError,
              runResult,
              onStageChange: setRunStage,
              onRun: handleRun,
            }
          : {})}
        {...(activeStep === 'results'
          ? {
              sessionId,
              runStatus,
              runError,
              runResult,
            }
          : {})}
      />
    </AppShell>
  )
}

export default App
