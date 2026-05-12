import styles from '../features/panels.module.css'

type EvidenceLink = {
  id?: string
  source_file_id?: string
  reference?: string
}

type EvidenceLinkBadgeProps = {
  links?: EvidenceLink[]
}

export function EvidenceLinkBadge({ links }: EvidenceLinkBadgeProps) {
  if (!links || links.length === 0) {
    return <span className={styles.badgeNeutral}>No evidence</span>
  }

  const references = links
    .map((link) => link.reference)
    .filter((ref): ref is string => Boolean(ref))

  if (!references.length) {
    return <span className={styles.badgeNeutral}>Evidence</span>
  }

  return (
    <span className={styles.evidenceBadge} title={references.join(' | ')}>
      {references.join(' | ')}
    </span>
  )
}
