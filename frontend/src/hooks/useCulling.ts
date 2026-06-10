import { useCallback, useRef, useState } from 'react'
import type { Cluster } from '../types'

interface UndoEntry {
  rejected: ReadonlySet<number>
  focusIndex: number
}

const UNDO_LIMIT = 200

export function useCulling() {
  const [rejected, setRejected] = useState<ReadonlySet<number>>(new Set())
  const [focusIndex, setFocusIndex] = useState(0)
  const undoStack = useRef<UndoEntry[]>([])

  const record = useCallback(
    (current: ReadonlySet<number>, index: number) => {
      undoStack.current.push({ rejected: current, focusIndex: index })
      if (undoStack.current.length > UNDO_LIMIT) undoStack.current.shift()
    },
    [],
  )

  const toggleReject = useCallback(
    (id: number) => {
      record(rejected, focusIndex)
      const next = new Set(rejected)
      if (next.has(id)) {
        next.delete(id)
      } else {
        next.add(id)
      }
      setRejected(next)
    },
    [rejected, focusIndex, record],
  )

  const keepOnly = useCallback(
    (cluster: Cluster, keeperId: number) => {
      record(rejected, focusIndex)
      const next = new Set(rejected)
      for (const photo of cluster.photos) {
        if (photo.id === keeperId) {
          next.delete(photo.id)
        } else {
          next.add(photo.id)
        }
      }
      setRejected(next)
    },
    [rejected, focusIndex, record],
  )

  const acceptSuggestion = useCallback(
    (cluster: Cluster) => keepOnly(cluster, cluster.suggestedKeeperId),
    [keepOnly],
  )

  const undo = useCallback(() => {
    const entry = undoStack.current.pop()
    if (!entry) return
    setRejected(entry.rejected)
    setFocusIndex(entry.focusIndex)
  }, [])

  const reset = useCallback(() => {
    undoStack.current = []
    setRejected(new Set())
    setFocusIndex(0)
  }, [])

  return {
    rejected,
    focusIndex,
    setFocusIndex,
    toggleReject,
    keepOnly,
    acceptSuggestion,
    undo,
    reset,
  }
}

export type Culling = ReturnType<typeof useCulling>
