import type { StepDefinition, StepKey } from '../app/types'
import styles from './SideNav.module.css'

type SideNavProps = {
  steps: StepDefinition[]
  activeStep: StepKey
  onSelect: (step: StepKey) => void
}

function SideNav({ steps, activeStep, onSelect }: SideNavProps) {
  return (
    <div className={styles.sideNav}>
      <div className={styles.brandBlock}>
        <h2 className={styles.brandTitle}>Audit Workflow</h2>
        <p className={styles.brandSub}>v1.0.0-mvp</p>
      </div>
      <nav className={styles.nav} aria-label="Workflow">
        {steps.map((step) => (
          <button
            key={step.key}
            type="button"
            className={`${styles.navItem} ${
              step.key === activeStep ? styles.navItemActive : ''
            }`}
            onClick={() => onSelect(step.key)}
          >
            {step.label}
          </button>
        ))}
      </nav>
      <div className={styles.footer}>
        <div className={styles.statusPill}>
          <span className={styles.statusDot} aria-hidden="true" />
          System Operational
        </div>
      </div>
    </div>
  )
}

export default SideNav
