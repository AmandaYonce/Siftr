import type { Summary } from '../types'
import { formatBytes } from '../format'

interface SummaryBarProps {
  summary: Summary
  threshold: number
  onThresholdChange: (value: number) => void
  onReset: () => void
  refreshing: boolean
}

export function SummaryBar({
  summary,
  threshold,
  onThresholdChange,
  onReset,
  refreshing,
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
