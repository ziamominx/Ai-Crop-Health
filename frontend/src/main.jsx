import React from 'react'
import ReactDOM from 'react-dom/client'
import './index.css'
import AgricureApp from './App.jsx'
import { setAuthToken } from './api/client.js'

/* GitHub Pages build: install the bundled-data API shim (and restore a session
   if this tab already has one) BEFORE the app mounts. Dynamically imported so the
   ~100 kB fixture file never ships in the normal local build. */
const STATIC_DEMO = import.meta.env.VITE_STATIC_DEMO === 'true'

async function boot() {
  if (STATIC_DEMO) {
    try {
      const { installStaticDemoApi, staticDemoToken } = await import('./demo/staticApi.js')
      installStaticDemoApi()
      const token = staticDemoToken()
      if (token) setAuthToken(token)
      document.documentElement.dataset.staticDemo = 'true'
    } catch (err) {
      // Never block the app on the demo shim — the banner will explain the state.
      console.error('[Agricure] static demo API failed to load:', err)
    }
  }

  ReactDOM.createRoot(document.getElementById('root')).render(
    <React.StrictMode>
      <AgricureApp />
    </React.StrictMode>,
  )
}

boot()
