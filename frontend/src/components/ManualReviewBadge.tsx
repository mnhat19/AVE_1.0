import styles from '../features/panels.module.css'

type ManualReviewBadgeProps = {
  label?: string
}

export function ManualReviewBadge({ label = 'Manual review' }: ManualReviewBadgeProps) {
  return <span className={styles.manualReviewBadge}>{label}</span>
}
