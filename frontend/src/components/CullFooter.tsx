import type { Cluster } from '../types'
import { formatBytes } from '../format'

interface CullFooterProps {
  clusters: Cluster[]
  rejected: ReadonlySet<number>
  onApply: () => void
  applying: boolean
}

export function CullFooter({
  clusters,
  rejected,
  onApply,
  applying,
}: CullFooterProps) {
  let keeping = 0
  let rejecting = 0
  let bytes = 0
  for (const cluster of clusters) {
    for (const photo of cluster.photos) {
      if (rejected.has(photo.id)) {
        rejecting += 1
        bytes += photo.bytes
      } else {
        keeping += 1
      }
    }
  }

  return (
    <footer className="cull-footer">
      <span>
        Keeping <strong>{keeping.toLocaleString()}</strong> · Rejecting{' '}
        <strong>{rejecting.toLocaleString()}</strong>
        {rejecting > 0 && <> · ~{formatBytes(bytes)} to reclaim</>}
      </span>
      <button
        className="apply-button"
        onClick={onApply}
        disabled={rejecting === 0 || applying}
      >
        {applying ? 'Moving…' : `Apply (move ${rejecting} to _rejects/)`}
      </button>
    </footer>
  )
}
