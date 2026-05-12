export const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000'

export const MOCK_MODE = import.meta.env.VITE_MOCK_MODE === 'true'
const SHOULD_MOCK_ON_FAILURE = MOCK_MODE || import.meta.env.DEV

export type ApiError = Error & { status?: number }

export type HealthResponse = {
  status: string
  llm_provider?: string
}

export type CreateSessionResponse = {
  session_id: string
  status: string
}

export type SessionSummaryResponse = {
  session_id: string
  status: string
  created_at?: string
  last_active_at?: string
  bundles_count: number
  files_count: number
}

export type UploadFileResult = {
  file_id: string
  filename: string
  format: string
  stage: string
  status: string
}

export type UploadResponse = {
  session_id: string
  files: UploadFileResult[]
  validation?: unknown
}

export type SessionFilesResponse = {
  session_id: string
  files: UploadFileResult[]
}

export type RunResponse = {
  session_id: string
  stage: string
  findings_count: number
  anomalies_count: number
  consolidated_count: number
  output_paths?: Record<string, string>
  changelog?: string[]
  audit_tasks?: unknown[]
  execution_plan?: Record<string, unknown>
}

export type Finding = {
  id: string
  stage: string
  description: string
  severity: string
  status: string
  confidence_score: number
  evidence_links?: { id?: string; source_file_id?: string; reference?: string }[]
  materiality?: string | null
  review_flag?: boolean
}

export type FeedbackAction = 'ACCEPT' | 'REJECT' | 'MODIFY'

export type FeedbackResponse = {
  status: string
  finding_id: string
  action: FeedbackAction
  feedback_id?: string
}

const createMockSessionId = () =>
  `MOCK-${Math.random().toString(36).slice(2, 8).toUpperCase()}`

const mockFindings: Finding[] = [
  {
    id: 'FND-014',
    stage: 'INTERIM',
    description: 'Revenue cut-off mismatch detected in Q2 entries.',
    severity: 'HIGH',
    status: 'OPEN',
    confidence_score: 0.78,
    materiality: 'MATERIAL',
    review_flag: false,
    evidence_links: [{ reference: 'Sheet1!Row 10' }],
  },
  {
    id: 'FND-021',
    stage: 'FIELDWORK',
    description: 'Policy control missing sign-off evidence.',
    severity: 'MEDIUM',
    status: 'IN_PROGRESS',
    confidence_score: 0.64,
    materiality: 'IMMATERIAL',
    review_flag: true,
    evidence_links: [{ reference: 'Page 2' }],
  },
  {
    id: 'FND-033',
    stage: 'FIELDWORK',
    description: 'Journal entry anomaly in vendor reconciliation.',
    severity: 'LOW',
    status: 'OPEN',
    confidence_score: 0.52,
    materiality: 'IMMATERIAL',
    review_flag: false,
    evidence_links: [],
  },
]

const buildMockRun = (sessionId: string): RunResponse => ({
  session_id: sessionId,
  stage: 'BOTH',
  findings_count: mockFindings.length,
  anomalies_count: 4,
  consolidated_count: 2,
  changelog: ['Mock run completed. No API detected.'],
  audit_tasks: [
    { name: 'Document Extraction', agent: 'Doc Agent', priority: 'High', status: 'Done' },
    { name: 'Control Testing', agent: 'Audit Agent', priority: 'High', status: 'Done' },
  ],
})

const isNetworkError = (error: unknown) => error instanceof TypeError

const requestJson = async <T>(path: string, options?: RequestInit) => {
  const response = await fetch(`${API_BASE_URL}${path}`, options)
  const contentType = response.headers.get('content-type') ?? ''
  const isJson = contentType.includes('application/json')
  const data = isJson ? await response.json() : await response.text()

  if (!response.ok) {
    let detail = 'Request failed'
    if (typeof data === 'string') {
      detail = data
    } else if (data && typeof data === 'object' && 'detail' in data) {
      const rawDetail = (data as { detail?: unknown }).detail
      if (typeof rawDetail === 'string') {
        detail = rawDetail
      } else if (rawDetail && typeof rawDetail === 'object') {
        const message = (rawDetail as { message?: string }).message
        const error = (rawDetail as { error?: string }).error
        detail = [message, error].filter(Boolean).join(': ') || detail
      }
    }

    const error = new Error(detail) as ApiError
    error.status = response.status
    throw error
  }

  return data as T
}

export const getErrorMessage = (error: unknown, fallback: string) => {
  if (error instanceof Error) {
    return error.message || fallback
  }
  return fallback
}

export const getHealth = async () => {
  if (MOCK_MODE) {
    return { status: 'ok', llm_provider: 'mock' }
  }

  try {
    return await requestJson<HealthResponse>('/health')
  } catch (error) {
    if (SHOULD_MOCK_ON_FAILURE && isNetworkError(error)) {
      return { status: 'ok', llm_provider: 'mock' }
    }
    throw error
  }
}

export const createSession = async () => {
  if (MOCK_MODE) {
    return { session_id: createMockSessionId(), status: 'created' }
  }

  try {
    return await requestJson<CreateSessionResponse>('/api/v1/sessions', {
      method: 'POST',
    })
  } catch (error) {
    if (SHOULD_MOCK_ON_FAILURE && isNetworkError(error)) {
      return { session_id: createMockSessionId(), status: 'created' }
    }
    throw error
  }
}

export const getSessionSummary = async (sessionId: string) => {
  if (MOCK_MODE) {
    return {
      session_id: sessionId,
      status: 'mock',
      bundles_count: 0,
      files_count: 0,
    }
  }

  try {
    return await requestJson<SessionSummaryResponse>(
      `/api/v1/sessions/${sessionId}`
    )
  } catch (error) {
    if (SHOULD_MOCK_ON_FAILURE && isNetworkError(error)) {
      return {
        session_id: sessionId,
        status: 'mock',
        bundles_count: 0,
        files_count: 0,
      }
    }
    throw error
  }
}

export const getSessionFiles = async (sessionId: string) => {
  if (MOCK_MODE) {
    return { session_id: sessionId, files: [] }
  }

  try {
    return await requestJson<SessionFilesResponse>(
      `/api/v1/sessions/${sessionId}/files`
    )
  } catch (error) {
    if (SHOULD_MOCK_ON_FAILURE && isNetworkError(error)) {
      return { session_id: sessionId, files: [] }
    }
    throw error
  }
}

export const uploadSessionFiles = async (
  sessionId: string,
  files: File[],
  bundleId?: string
) => {
  if (MOCK_MODE) {
    return {
      session_id: sessionId,
      files: files.map((file) => ({
        file_id: `mock-${file.name}`,
        filename: file.name,
        format: file.name.split('.').pop()?.toUpperCase() ?? 'FILE',
        stage: 'BOTH',
        status: 'MOCKED',
      })),
      validation: { status: 'MOCKED', missing: [] },
    }
  }

  const formData = new FormData()
  files.forEach((file) => formData.append('files', file))
  if (bundleId) {
    formData.append('bundle_id', bundleId)
  }

  try {
    return await requestJson<UploadResponse>(
      `/api/v1/sessions/${sessionId}/upload`,
      {
        method: 'POST',
        body: formData,
      }
    )
  } catch (error) {
    if (SHOULD_MOCK_ON_FAILURE && isNetworkError(error)) {
      return {
        session_id: sessionId,
        files: files.map((file) => ({
          file_id: `mock-${file.name}`,
          filename: file.name,
          format: file.name.split('.').pop()?.toUpperCase() ?? 'FILE',
          stage: 'BOTH',
          status: 'MOCKED',
        })),
        validation: { status: 'MOCKED', missing: [] },
      }
    }
    throw error
  }
}

export const runSession = async (sessionId: string, stage: string) => {
  if (MOCK_MODE) {
    return buildMockRun(sessionId)
  }

  const body = new URLSearchParams({ stage })

  try {
    return await requestJson<RunResponse>(`/api/v1/sessions/${sessionId}/run`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/x-www-form-urlencoded',
      },
      body,
    })
  } catch (error) {
    if (SHOULD_MOCK_ON_FAILURE && isNetworkError(error)) {
      return buildMockRun(sessionId)
    }
    throw error
  }
}

export const getFindings = async (sessionId: string) => {
  if (MOCK_MODE) {
    return mockFindings
  }

  try {
    return await requestJson<Finding[]>(
      `/api/v1/sessions/${sessionId}/findings`
    )
  } catch (error) {
    if (SHOULD_MOCK_ON_FAILURE && isNetworkError(error)) {
      return mockFindings
    }
    throw error
  }
}

export const submitFeedback = async (
  findingId: string,
  action: FeedbackAction,
  comment: string,
  correctedValue?: string
) => {
  if (MOCK_MODE) {
    return { status: 'feedback_recorded', finding_id: findingId, action }
  }

  const body = new URLSearchParams({ action, comment })
  if (correctedValue) {
    body.set('corrected_value', correctedValue)
  }
  try {
    return await requestJson<FeedbackResponse>(
      `/api/v1/findings/${findingId}/feedback`,
      {
        method: 'POST',
        headers: {
          'Content-Type': 'application/x-www-form-urlencoded',
        },
        body,
      }
    )
  } catch (error) {
    if (SHOULD_MOCK_ON_FAILURE && isNetworkError(error)) {
      return { status: 'feedback_recorded', finding_id: findingId, action }
    }
    throw error
  }
}
