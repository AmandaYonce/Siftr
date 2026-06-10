import type { Summary } from '../types'
import { formatBytes } from '../format'

interface SummaryBarProps {
  summary: Summary
  threshold: number
  onThresholdChange: (value: number) => void
  onReset: () => void
  refreshing: boolean
  mode: 'focus' | 'grid'
  onModeChange: (mode: 'focus' | 'grid') => void
}

export function SummaryBar({
  summary,
  threshold,
  onThresholdChange,
  onReset,
  refreshing,
  mode,
  onModeChange,
}: SummaryBarProps) {
  return (
    <header className="summary-bar">
      <span className="brand brand--small">Siftr</span>
      <div className="summary-stats">
        <Stat value={summary.photos} label="photos" />
        <Stat value={summary.clusters} label="clusters" />
        <Stat value={summary.duplicates} label="likely duplicates" />
        <Stat value={formatBytes(summary.reclaimableBytes)} label="reclaimable" />
      </div>
      <div className="mode-toggle" role="group" aria-label="Review mode">
        <button
          className={mode === 'focus' ? 'mode-button mode-button--active' : 'mode-button'}
          onClick={() => onModeChange('focus')}
        >
          Focus
        </button>
        <button
          className={mode === 'grid' ? 'mode-button mode-button--active' : 'mode-button'}
          onClick={() => onModeChange('grid')}
        >
          Grid
        </button>
      </div>
      <label className={`threshold-control${refreshing ? ' threshold-control--busy' : ''}`}>
        Similarity
        <input
          type="range"
          min={0}
          max={16}
          value={threshold}
          onChange={(e) => onThresholdChange(Number(e.target.value))}
        />
        <span className="threshold-value">{threshold}</span>
      </label>
      <button className="link-button" onClick={onReset}>
        Scan another folder
      </button>
    </header>
  )
}

function Stat({ value, label }: { value: number | string; label: string }) {
  return (
    <span className="stat">
      <strong>{value.toLocaleString()}</strong> {label}
    </span>
  )
}
