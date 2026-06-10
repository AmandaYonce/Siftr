import { useEffect, useState } from 'react'
import type { Cluster, Photo } from '../types'
import type { Culling } from '../hooks/useCulling'
import { formatBytes } from '../format'

interface FocusModeProps {
  clusters: Cluster[]
  culling: Culling
  shortcutsDisabled: boolean
}

export function FocusMode({
  clusters,
  culling,
  shortcutsDisabled,
}: FocusModeProps) {
  const { focusIndex, setFocusIndex } = culling
  const index = Math.max(Math.min(focusIndex, clusters.length - 1), 0)
  const cluster = clusters[index]

  if (!cluster) return null
  return (
    <FocusCluster
      key={cluster.id}
      cluster={cluster}
      clusterIndex={index}
      clusterCount={clusters.length}
      culling={culling}
      shortcutsDisabled={shortcutsDisabled}
      onAdvance={() =>
        setFocusIndex(Math.min(index + 1, clusters.length - 1))
      }
      onBack={() => setFocusIndex(Math.max(index - 1, 0))}
    />
  )
}

interface FocusClusterProps {
  cluster: Cluster
  clusterIndex: number
  clusterCount: number
  culling: Culling
  shortcutsDisabled: boolean
  onAdvance: () => void
  onBack: () => void
}

function FocusCluster({
  cluster,
  clusterIndex,
  clusterCount,
  culling,
  shortcutsDisabled,
  onAdvance,
  onBack,
}: FocusClusterProps) {
  const { rejected, toggleReject, keepOnly, acceptSuggestion, undo } = culling
  const [selection, setSelection] = useState(() =>
    Math.max(
      cluster.photos.findIndex((p) => p.id === cluster.suggestedKeeperId),
      0,
    ),
  )
  const selected = cluster.photos[selection]

  useEffect(() => {
    if (shortcutsDisabled) return
    function onKey(event: KeyboardEvent) {
      if (event.metaKey || event.ctrlKey || event.altKey) return
      const target = event.target as HTMLElement | null
      if (
        target?.closest('input, button, select, textarea, [contenteditable]')
      ) {
        return
      }
      switch (event.key) {
        case 'ArrowLeft':
          event.preventDefault()
          setSelection((i) => Math.max(i - 1, 0))
          break
        case 'ArrowRight':
          event.preventDefault()
          setSelection((i) => Math.min(i + 1, cluster.photos.length - 1))
          break
        case ' ':
          event.preventDefault()
          toggleReject(selected.id)
          break
        case 'k':
        case 'K':
          keepOnly(cluster, selected.id)
          break
        case 'Enter':
          acceptSuggestion(cluster)
          onAdvance()
          break
        case 'u':
        case 'U':
          undo()
          break
        case 'n':
        case 'N':
          onAdvance()
          break
        case 'p':
        case 'P':
          onBack()
          break
      }
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [
    cluster,
    selected,
    shortcutsDisabled,
    toggleReject,
    keepOnly,
    acceptSuggestion,
    undo,
    onAdvance,
    onBack,
  ])

  return (
    <div className="focus-mode">
      <p className="focus-progress">
        Cluster {clusterIndex + 1} of {clusterCount}
        {cluster.photos.length > 1 &&
          ` · ${cluster.photos.length} similar photos`}
      </p>
      <p className="focus-hint">
        Press <kbd>?</kbd> for keyboard shortcuts
      </p>
      <FocusPreview
        photo={selected}
        isKeeper={selected.id === cluster.suggestedKeeperId}
        isRejected={rejected.has(selected.id)}
      />
      <div className="focus-strip">
        {cluster.photos.map((photo, index) => (
          <button
            key={photo.id}
            className={stripItemClass(photo, cluster, rejected, index === selection)}
            onClick={(event) => {
              setSelection(index)
              event.currentTarget.blur()
            }}
          >
            <img src={photo.thumbnailUrl} alt={photo.filename} loading="lazy" />
          </button>
        ))}
      </div>
    </div>
  )
}

function stripItemClass(
  photo: Photo,
  cluster: Cluster,
  rejected: ReadonlySet<number>,
  isSelected: boolean,
): string {
  const classes = ['strip-item']
  if (isSelected) classes.push('strip-item--selected')
  if (rejected.has(photo.id)) classes.push('strip-item--rejected')
  if (photo.id === cluster.suggestedKeeperId) classes.push('strip-item--keeper')
  return classes.join(' ')
}

function FocusPreview({
  photo,
  isKeeper,
  isRejected,
}: {
  photo: Photo
  isKeeper: boolean
  isRejected: boolean
}) {
  return (
    <figure className="focus-preview">
      <div className="focus-preview-frame">
        {isKeeper && <span className="keeper-badge">Suggested keeper</span>}
        {isRejected && <span className="rejected-badge">Rejected</span>}
        <img src={photo.thumbnailUrl} alt={photo.filename} />
      </div>
      <figcaption>
        <strong>{photo.filename}</strong> · sharpness{' '}
        {Math.round(photo.sharpness)} · {photo.width}×{photo.height} ·{' '}
        {formatBytes(photo.bytes)}
        {photo.faceCount > 0 &&
          ` · ${photo.faceCount} ${photo.faceCount === 1 ? 'face' : 'faces'}`}
      </figcaption>
    </figure>
  )
}
