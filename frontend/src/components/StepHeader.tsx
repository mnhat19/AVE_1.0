import type { StepDefinition, StepKey } from '../app/types'
import Stepper from './Stepper'
import styles from './StepHeader.module.css'

type StepHeaderProps = {
  steps: StepDefinition[]
  activeStep: StepKey
  title: string
  description: string
}

function StepHeader({ steps, activeStep, title, description }: StepHeaderProps) {
  return (
    <section className={styles.header}>
      <div className={styles.breadcrumbs}>
        <span className="text-label">Wizard</span>
        <span className={styles.breadcrumbDivider}>&gt;</span>
        <span className="text-label">{title}</span>
      </div>
      <h1 className={`text-h1 ${styles.title}`}>{title}</h1>
      <p className={`text-body-lg ${styles.description}`}>{description}</p>
      <Stepper steps={steps} activeStep={activeStep} />
    </section>
  )
}

export default StepHeader
