import { useCallback, useEffect, useRef, useState } from 'react'
import {
  ApiError,
  applyRejects,
  fetchClusters,
  postDecisions,
  scanFolder,
  undoApply,
} from './api'
import type { ApplyResponse, ClustersResponse } from './types'
import { useCulling } from './hooks/useCulling'
import { StartScreen } from './components/StartScreen'
import { SummaryBar } from './components/SummaryBar'
import { FocusMode } from './components/FocusMode'
import { GridMode } from './components/GridMode'
import { CullFooter } from './components/CullFooter'
import { AppliedScreen } from './components/AppliedScreen'
import { ShortcutOverlay } from './components/ShortcutOverlay'
import './App.css'

type Screen = 'start' | 'scanning' | 'results' | 'applied'
type Mode = 'focus' | 'grid'

const DEFAULT_THRESHOLD = 9
const DECISIONS_DEBOUNCE_MS = 400

function App() {
  const [screen, setScreen] = useState<Screen>('start')
  const [mode, setMode] = useState<Mode>('focus')
  const [error, setError] = useState<string | null>(null)
  const [data, setData] = useState<ClustersResponse | null>(null)
  const [threshold, setThreshold] = useState(DEFAULT_THRESHOLD)
  const [preferFaces, setPreferFaces] = useState(false)
  const [refreshing, setRefreshing] = useState(false)
  const [applied, setApplied] = useState<ApplyResponse | null>(null)
  const [applying, setApplying] = useState(false)
  const [undoing, setUndoing] = useState(false)
  const [applyError, setApplyError] = useState<string | null>(null)
  const [showShortcuts, setShowShortcuts] = useState(false)
  const clusterRequestSeq = useRef(0)
  const decisionsChain = useRef<Promise<unknown>>(Promise.resolve())
  const culling = useCulling()
  const { rejected, reset: resetCulling } = culling

  useEffect(() => {
    if (screen !== 'results') return
    const timer = setTimeout(() => {
      const reject = [...rejected]
      // Chained so syncs reach the server in order; a missed sync is
      // re-sent on the next change.
      decisionsChain.current = decisionsChain.current
        .then(() => postDecisions(reject))
        .catch(() => {})
    }, DECISIONS_DEBOUNCE_MS)
    return () => clearTimeout(timer)
  }, [rejected, screen])

  const handleScan = useCallback(
    async (folder: string, recursive: boolean) => {
      setScreen('scanning')
      setError(null)
      try {
        await scanFolder(folder, threshold, recursive)
        setData(await fetchClusters(threshold, preferFaces))
        resetCulling()
        setMode('focus')
        setScreen('results')
      } catch (err) {
        setError(
          err instanceof ApiError
            ? err.message
            : 'Something went wrong during the scan.',
        )
        setScreen('start')
      }
    },
    [threshold, preferFaces, resetCulling],
  )

  const refreshClusters = useCallback(
    async (nextThreshold: number, nextPreferFaces: boolean) => {
      setRefreshing(true)
      // Rapid control changes can resolve out of order; only the latest
      // request is allowed to update the screen.
      const seq = ++clusterRequestSeq.current
      try {
        const next = await fetchClusters(nextThreshold, nextPreferFaces)
        if (seq === clusterRequestSeq.current) setData(next)
      } catch {
        // Keep showing the previous clustering if the refresh fails.
      } finally {
        if (seq === clusterRequestSeq.current) setRefreshing(false)
      }
    },
    [],
  )

  const handleThresholdChange = useCallback(
    (value: number) => {
      setThreshold(value)
      void refreshClusters(value, preferFaces)
    },
    [preferFaces, refreshClusters],
  )

  const handlePreferFacesChange = useCallback(
    (value: boolean) => {
      setPreferFaces(value)
      void refreshClusters(threshold, value)
    },
    [threshold, refreshClusters],
  )

  const handleApply = useCallback(async () => {
    setApplying(true)
    setApplyError(null)
    try {
      // The final sync goes through the same chain as the debounced
      // ones, so an older in-flight update can never land after it.
      decisionsChain.current = decisionsChain.current
        .catch(() => {})
        .then(() => postDecisions([...rejected]))
      await decisionsChain.current
      setApplied(await applyRejects())
      setScreen('applied')
    } catch (err) {
      setApplyError(
        err instanceof ApiError ? err.message : 'Apply failed.',
      )
    } finally {
      setApplying(false)
    }
  }, [rejected])

  const handleUndo = useCallback(async () => {
    setUndoing(true)
    setApplyError(null)
    try {
      await undoApply()
      await postDecisions([...rejected])
      setApplied(null)
      setScreen('results')
    } catch (err) {
      setApplyError(
        err instanceof ApiError ? err.message : 'Undo failed.',
      )
    } finally {
      setUndoing(false)
    }
  }, [rejected])

  const handleReset = useCallback(() => {
    setScreen('start')
    setData(null)
    setError(null)
    setApplied(null)
    setApplyError(null)
    resetCulling()
  }, [resetCulling])

  if (screen === 'start') {
    return <StartScreen onScan={handleScan} error={error} />
  }

  if (screen === 'applied' && applied) {
    return (
      <AppliedScreen
        result={applied}
        onUndo={handleUndo}
        undoing={undoing}
        onStartOver={handleReset}
        error={applyError}
      />
    )
  }

  if (screen === 'scanning' || data === null) {
    return (
      <div className="loading-screen">
        <div className="spinner" aria-hidden="true" />
        <p>
          Scanning photos… first runs hash and score every image, so large
          folders take a minute.
        </p>
        <p className="loading-hint">
          Re-scans of the same folder are nearly instant.
        </p>
      </div>
    )
  }

  return (
    <div className="results-screen">
      <SummaryBar
        summary={data.summary}
        threshold={threshold}
        onThresholdChange={handleThresholdChange}
        preferFaces={preferFaces}
        onPreferFacesChange={handlePreferFacesChange}
        onReset={handleReset}
        refreshing={refreshing}
        mode={mode}
        onModeChange={setMode}
      />
      {mode === 'focus' ? (
        <FocusMode
          clusters={data.clusters}
          culling={culling}
          shortcutsDisabled={showShortcuts}
        />
      ) : (
        <GridMode clusters={data.clusters} culling={culling} />
      )}
      <ShortcutOverlay open={showShortcuts} onToggle={setShowShortcuts} />
      {applyError && (
        <p className="error-message error-message--floating" role="alert">
          {applyError}
        </p>
      )}
      <CullFooter
        clusters={data.clusters}
        rejected={rejected}
        onApply={handleApply}
        applying={applying}
      />
    </div>
  )
}

export default App
