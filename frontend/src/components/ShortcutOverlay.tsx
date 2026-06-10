import { useEffect, useRef } from 'react'

const SHORTCUTS: [string, string][] = [
  ['← →', 'Move selection within the cluster'],
  ['Space', 'Toggle keep / reject on the selected photo'],
  ['K', 'Keep only the selected photo, reject the rest'],
  ['Enter', 'Accept the suggestion and go to the next cluster'],
  ['N / P', 'Next / previous cluster without deciding'],
  ['U', 'Undo the last change'],
  ['?', 'Show or hide this overlay'],
]

interface ShortcutOverlayProps {
  open: boolean
  onToggle: (open: boolean) => void
}

export function ShortcutOverlay({ open, onToggle }: ShortcutOverlayProps) {
  const panelRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    function onKey(event: KeyboardEvent) {
      if (event.metaKey || event.ctrlKey || event.altKey) return
      if (open && event.key === 'Escape') {
        onToggle(false)
        return
      }
      const target = event.target as HTMLElement | null
      if (target?.closest('input, textarea, select, [contenteditable]')) {
        return
      }
      if (event.key === '?') onToggle(!open)
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [open, onToggle])

  useEffect(() => {
    if (open) panelRef.current?.focus()
  }, [open])

  if (!open) return null
  return (
    <div
      className="shortcut-overlay"
      role="dialog"
      aria-modal="true"
      aria-label="Keyboard shortcuts"
      onClick={() => onToggle(false)}
    >
      <div
        ref={panelRef}
        tabIndex={-1}
        className="shortcut-panel"
        onClick={(e) => e.stopPropagation()}
      >
        <h2>Keyboard shortcuts</h2>
        <dl>
          {SHORTCUTS.map(([keys, description]) => (
            <div key={keys} className="shortcut-row">
              <dt>
                <kbd>{keys}</kbd>
              </dt>
              <dd>{description}</dd>
            </div>
          ))}
        </dl>
        <p className="shortcut-note">
          Shortcuts work in focus mode; grid mode is point and click.
        </p>
      </div>
    </div>
  )
}
