import { useCallback, useEffect, useRef, useState } from 'react'
import { ApiError, fetchClusters, postDecisions, scanFolder } from './api'
import type { ClustersResponse } from './types'
import { useCulling } from './hooks/useCulling'
import { StartScreen } from './components/StartScreen'
import { SummaryBar } from './components/SummaryBar'
import { FocusMode } from './components/FocusMode'
import { GridMode } from './components/GridMode'
import { CullFooter } from './components/CullFooter'
import './App.css'

type Screen = 'start' | 'scanning' | 'results'
type Mode = 'focus' | 'grid'

const DEFAULT_THRESHOLD = 9
const DECISIONS_DEBOUNCE_MS = 400

function App() {
  const [screen, setScreen] = useState<Screen>('start')
  const [mode, setMode] = useState<Mode>('focus')
  const [error, setError] = useState<string | null>(null)
  const [data, setData] = useState<ClustersResponse | null>(null)
  const [threshold, setThreshold] = useState(DEFAULT_THRESHOLD)
  const [refreshing, setRefreshing] = useState(false)
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
        setData(await fetchClusters(threshold))
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
    [threshold, resetCulling],
  )

  const handleThresholdChange = useCallback(async (value: number) => {
    setThreshold(value)
    setRefreshing(true)
    // Rapid slider moves can resolve out of order; only the latest
    // request is allowed to update the screen.
    const seq = ++clusterRequestSeq.current
    try {
      const next = await fetchClusters(value)
      if (seq === clusterRequestSeq.current) setData(next)
    } catch {
      // Keep showing the previous clustering if the refresh fails.
    } finally {
      if (seq === clusterRequestSeq.current) setRefreshing(false)
    }
  }, [])

  const handleReset = useCallback(() => {
    setScreen('start')
    setData(null)
    setError(null)
    resetCulling()
  }, [resetCulling])

  if (screen === 'start') {
    return <StartScreen onScan={handleScan} error={error} />
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
        onReset={handleReset}
        refreshing={refreshing}
        mode={mode}
        onModeChange={setMode}
      />
      {mode === 'focus' ? (
        <FocusMode clusters={data.clusters} culling={culling} />
      ) : (
        <GridMode clusters={data.clusters} culling={culling} />
      )}
      <CullFooter clusters={data.clusters} rejected={rejected} />
    </div>
  )
}

export default App
