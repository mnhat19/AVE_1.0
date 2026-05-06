import type { StepDefinition, StepKey } from '../app/types'
import styles from './Stepper.module.css'

type StepperProps = {
  steps: StepDefinition[]
  activeStep: StepKey
}

function Stepper({ steps, activeStep }: StepperProps) {
  const activeIndex = steps.findIndex((step) => step.key === activeStep)

  return (
    <ol className={styles.stepper}>
      {steps.map((step, index) => {
        const isActive = step.key === activeStep
        const isCompleted = index < activeIndex

        return (
          <li
            key={step.key}
            className={`${styles.step} ${
              isActive ? styles.stepActive : isCompleted ? styles.stepCompleted : ''
            }`}
          >
            <span className={styles.stepIndex}>{index + 1}</span>
            {step.label}
          </li>
        )
      })}
    </ol>
  )
}

export default Stepper
