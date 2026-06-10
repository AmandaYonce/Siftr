import type { Cluster, Photo } from '../types'
import { formatBytes, formatTakenAt } from '../format'

interface ClusterGridProps {
  clusters: Cluster[]
}

export function ClusterGrid({ clusters }: ClusterGridProps) {
  return (
    <div className="cluster-grid">
      {clusters.map((cluster) => (
        <ClusterRow key={cluster.id} cluster={cluster} />
      ))}
    </div>
  )
}

function ClusterRow({ cluster }: { cluster: Cluster }) {
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
          />
        ))}
      </div>
    </section>
  )
}

function PhotoCard({ photo, isKeeper }: { photo: Photo; isKeeper: boolean }) {
  return (
    <figure className={`photo-card${isKeeper ? ' photo-card--keeper' : ''}`}>
      {isKeeper && <span className="keeper-badge">Suggested keeper</span>}
      <img
        src={photo.thumbnailUrl}
        alt={photo.filename}
        loading="lazy"
        width={160}
        height={107}
      />
      <figcaption>
        <span className="photo-name" title={photo.filename}>
          {photo.filename}
        </span>
        <span className="photo-meta">
          sharpness {Math.round(photo.sharpness)} · {photo.width}×{photo.height} ·{' '}
          {formatBytes(photo.bytes)}
        </span>
        {photo.takenAt && <span className="photo-meta">{formatTakenAt(photo.takenAt)}</span>}
      </figcaption>
    </figure>
  )
}
