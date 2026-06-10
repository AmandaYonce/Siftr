import { useState } from 'react'
import type { FormEvent } from 'react'

interface StartScreenProps {
  onScan: (folder: string, recursive: boolean) => void
  error: string | null
}

export function StartScreen({ onScan, error }: StartScreenProps) {
  const [folder, setFolder] = useState('')
  const [recursive, setRecursive] = useState(false)

  function handleSubmit(event: FormEvent) {
    event.preventDefault()
    if (folder.trim()) onScan(folder.trim(), recursive)
  }

  return (
    <div className="start-screen">
      <h1 className="brand">Siftr</h1>
      <p className="tagline">
        Point Siftr at a folder of photos. It groups near-duplicates, scores
        sharpness, and helps you keep only the best shot from every burst.
      </p>
      <form className="start-form" onSubmit={handleSubmit}>
        <input
          type="text"
          value={folder}
          onChange={(e) => setFolder(e.target.value)}
          placeholder="/Users/you/Pictures/Vacation2026"
          aria-label="Folder path"
          autoFocus
        />
        <button type="submit" disabled={!folder.trim()}>
          Scan
        </button>
      </form>
      <label className="recursive-toggle">
        <input
          type="checkbox"
          checked={recursive}
          onChange={(e) => setRecursive(e.target.checked)}
        />
        Include subfolders
      </label>
      {error && <p className="error-message" role="alert">{error}</p>}
      <p className="safety-note">
        Non-destructive: Siftr never deletes photos. Rejects are moved to a{' '}
        <code>_rejects/</code> folder you can restore at any time.
      </p>
    </div>
  )
}
