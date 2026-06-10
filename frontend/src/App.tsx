import { useCallback, useRef, useState } from 'react'
import { ApiError, fetchClusters, scanFolder } from './api'
import type { ClustersResponse } from './types'
import { StartScreen } from './components/StartScreen'
import { SummaryBar } from './components/SummaryBar'
import { ClusterGrid } from './components/ClusterGrid'
import './App.css'

type Screen = 'start' | 'scanning' | 'results'

const DEFAULT_THRESHOLD = 9

function App() {
  const [screen, setScreen] = useState<Screen>('start')
  const [error, setError] = useState<string | null>(null)
  const [data, setData] = useState<ClustersResponse | null>(null)
  const [threshold, setThreshold] = useState(DEFAULT_THRESHOLD)
  const [refreshing, setRefreshing] = useState(false)
  const clusterRequestSeq = useRef(0)

  const handleScan = useCallback(
    async (folder: string, recursive: boolean) => {
      setScreen('scanning')
      setError(null)
      try {
        await scanFolder(folder, threshold, recursive)
        setData(await fetchClusters(threshold))
        setScreen('results')
      } catch (err) {
        setError(err instanceof ApiError ? err.message : 'Something went wrong during the scan.')
        setScreen('start')
      }
    },
    [threshold],
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
  }, [])

  if (screen === 'start') {
    return <StartScreen onScan={handleScan} error={error} />
  }

  if (screen === 'scanning' || data === null) {
    return (
      <div className="loading-screen">
        <div className="spinner" aria-hidden="true" />
        <p>Scanning photos… first runs hash and score every image, so large folders take a minute.</p>
        <p className="loading-hint">Re-scans of the same folder are nearly instant.</p>
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
      />
      <ClusterGrid clusters={data.clusters} />
    </div>
  )
}

export default App
