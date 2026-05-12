import styles from '../features/panels.module.css'

type MaterialityTagProps = {
  level?: string | null
}

export function MaterialityTag({ level }: MaterialityTagProps) {
  if (!level) {
    return <span className={styles.badgeNeutral}>Unknown</span>
  }

  const normalized = level.toUpperCase()
  const className =
    normalized === 'HIGHLY_MATERIAL'
      ? styles.materialityHigh
      : normalized === 'MATERIAL'
      ? styles.materialityMedium
      : styles.materialityLow

  return <span className={`${styles.materialityTag} ${className}`}>{normalized}</span>
}
