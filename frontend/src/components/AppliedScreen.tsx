import type { ApplyResponse } from '../types'
import { formatBytes } from '../format'

interface AppliedScreenProps {
  result: ApplyResponse
  onUndo: () => void
  undoing: boolean
  onStartOver: () => void
  error: string | null
}

export function AppliedScreen({
  result,
  onUndo,
  undoing,
  onStartOver,
  error,
}: AppliedScreenProps) {
  return (
    <div className="applied-screen">
      <div className="applied-check" aria-hidden="true">
        ✓
      </div>
      <h1>
        Moved {result.moved.toLocaleString()}{' '}
        {result.moved === 1 ? 'photo' : 'photos'} to <code>_rejects/</code>
      </h1>
      <p>
        {formatBytes(result.reclaimedBytes)} reclaimed. Nothing was deleted —
        every file is sitting in the <code>_rejects/</code> folder inside your
        scanned folder, and Undo puts them all back.
      </p>
      {error && <p className="error-message" role="alert">{error}</p>}
      <div className="applied-actions">
        <button className="undo-button" onClick={onUndo} disabled={undoing}>
          {undoing ? 'Restoring…' : 'Undo'}
        </button>
        <button className="link-button" onClick={onStartOver}>
          Scan another folder
        </button>
      </div>
    </div>
  )
}
