export type StepKey = 'session' | 'upload' | 'run' | 'results'

export type StepDefinition = {
  key: StepKey
  label: string
  title: string
  description: string
}

export type HealthStatus = 'ok' | 'warn' | 'unknown'

export type SessionStatus = 'idle' | 'creating' | 'ready' | 'error'

export type RunStatus = 'idle' | 'running' | 'success' | 'error'

export type RunStage = 'INTERIM' | 'FIELDWORK' | 'BOTH'
