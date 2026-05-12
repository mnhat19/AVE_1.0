import styles from '../features/panels.module.css'

type ConfidenceScoreProps = {
  score: number
}

export function ConfidenceScore({ score }: ConfidenceScoreProps) {
  const safeScore = Number.isFinite(score) ? Math.max(0, Math.min(score, 1)) : 0
  const percent = Math.round(safeScore * 100)

  return (
    <div className={styles.confidenceWrap}>
      <div className={styles.confidenceBar}>
        <div
          className={styles.confidenceFill}
          style={{ width: `${percent}%` }}
        />
      </div>
      <span className={styles.confidenceValue}>{percent}%</span>
    </div>
  )
}
