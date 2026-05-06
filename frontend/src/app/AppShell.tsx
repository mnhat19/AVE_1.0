import type { ReactNode } from 'react'

import SideNav from '../components/SideNav'
import TopBar from '../components/TopBar'
import type { HealthStatus, StepDefinition, StepKey } from './types'
import styles from './AppShell.module.css'

type AppShellProps = {
  steps: StepDefinition[]
  activeStep: StepKey
  onStepChange: (step: StepKey) => void
  sessionId: string
  healthStatus: HealthStatus
  apiBaseUrl: string
  mockMode: boolean
  children: ReactNode
}

function AppShell({
  steps,
  activeStep,
  onStepChange,
  sessionId,
  healthStatus,
  apiBaseUrl,
  mockMode,
  children,
}: AppShellProps) {
  return (
    <div className={styles.shell}>
      <header className={styles.header}>
        <TopBar
          sessionId={sessionId}
          healthStatus={healthStatus}
          apiBaseUrl={apiBaseUrl}
          mockMode={mockMode}
        />
      </header>
      <aside className={styles.sidebar}>
        <SideNav
          steps={steps}
          activeStep={activeStep}
          onSelect={onStepChange}
        />
      </aside>
      <main className={`${styles.main} bg-grid`}>
        <div className={styles.mainInner}>{children}</div>
      </main>
    </div>
  )
}

export default AppShell
