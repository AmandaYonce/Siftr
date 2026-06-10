import type { Cluster, Photo } from '../types'
import type { Culling } from '../hooks/useCulling'
import { formatBytes, formatTakenAt } from '../format'

interface GridModeProps {
  clusters: Cluster[]
  culling: Culling
}

export function GridMode({ clusters, culling }: GridModeProps) {
  return (
    <div className="cluster-grid">
      {clusters.map((cluster) => (
        <ClusterRow key={cluster.id} cluster={cluster} culling={culling} />
      ))}
    </div>
  )
}

function ClusterRow({
  cluster,
  culling,
}: {
  cluster: Cluster
  culling: Culling
}) {
  const isGroup = cluster.photos.length > 1
  return (
    <section className="cluster-row">
      <h2 className="cluster-heading">
        {isGroup ? `${cluster.photos.length} similar photos` : 'Unique photo'}
      </h2>
      <div className="cluster-photos">
        {cluster.photos.map((photo) => (
          <PhotoCard
            key={photo.id}
            photo={photo}
            isKeeper={isGroup && photo.id === cluster.suggestedKeeperId}
            isRejected={culling.rejected.has(photo.id)}
            onToggle={() => culling.toggleReject(photo.id)}
          />
        ))}
      </div>
    </section>
  )
}

function PhotoCard({
  photo,
  isKeeper,
  isRejected,
  onToggle,
}: {
  photo: Photo
  isKeeper: boolean
  isRejected: boolean
  onToggle: () => void
}) {
  const classes = ['photo-card']
  if (isKeeper) classes.push('photo-card--keeper')
  if (isRejected) classes.push('photo-card--rejected')

  return (
    <figure className={classes.join(' ')}>
      {isKeeper && <span className="keeper-badge">Suggested keeper</span>}
      {isRejected && <span className="rejected-badge">Rejected</span>}
      <button
        className="photo-toggle"
        onClick={onToggle}
        title={isRejected ? 'Click to keep' : 'Click to reject'}
      >
        <img
          src={photo.thumbnailUrl}
          alt={photo.filename}
          loading="lazy"
          width={160}
          height={107}
        />
      </button>
      <figcaption>
        <span className="photo-name" title={photo.filename}>
          {photo.filename}
        </span>
        <span className="photo-meta">
          sharpness {Math.round(photo.sharpness)} · {photo.width}×{photo.height} ·{' '}
          {formatBytes(photo.bytes)}
        </span>
        {photo.takenAt && (
          <span className="photo-meta">{formatTakenAt(photo.takenAt)}</span>
        )}
      </figcaption>
    </figure>
  )
}
