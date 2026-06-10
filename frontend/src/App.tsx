import { useEffect, useState } from 'react'
import './App.css'

function App() {
  const [apiStatus, setApiStatus] = useState<'checking' | 'connected' | 'offline'>('checking')

  useEffect(() => {
    fetch('/api/health')
      .then((res) => (res.ok ? setApiStatus('connected') : setApiStatus('offline')))
      .catch(() => setApiStatus('offline'))
  }, [])

  return (
    <main className="app">
      <h1>Siftr</h1>
      <p>Find near-duplicate photos, keep the sharpest, sweep the rest.</p>
      <p className={`api-status api-status--${apiStatus}`}>API: {apiStatus}</p>
    </main>
  )
}

export default App
