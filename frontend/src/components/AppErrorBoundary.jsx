import { Component } from 'react'
import { C } from '../api/theme.js'
import { AlertTriangle, RefreshCw } from '../api/icons.jsx'

/* Error boundary — a render crash shows a recoverable message instead of a white screen. */
export class AppErrorBoundary extends Component {
  constructor(props) {
    super(props)
    this.state = { error: null }
  }

  static getDerivedStateFromError(error) {
    return { error }
  }

  componentDidCatch(error, info) {
    console.error('[Agricure] UI crash:', error, info?.componentStack)
  }

  render() {
    if (this.state.error) {
      return (
        <div className="min-h-screen w-full flex items-center justify-center p-6" style={{ background: C.cream }}>
          <div className="ag-fade w-full max-w-md rounded-2xl p-8 text-center" style={{ background: C.white, border: `1px solid ${C.line}` }}>
            <div className="mx-auto mb-4 w-14 h-14 rounded-full flex items-center justify-center" style={{ background: '#fbeae6' }}>
              <AlertTriangle size={26} color={C.red} />
            </div>
            <h1 className="ag-display text-2xl mb-2" style={{ color: C.forest }}>Something went wrong</h1>
            <p className="ag-body text-sm mb-1" style={{ color: 'rgba(20,35,26,0.6)' }}>
              The interface hit an unexpected error.
            </p>
            <p className="ag-body text-xs mb-6" style={{ color: 'rgba(20,35,26,0.45)' }}>
              {String(this.state.error?.message || this.state.error).slice(0, 160)}
            </p>
            <button
              onClick={() => { this.setState({ error: null }); window.location.reload() }}
              className="ag-body inline-flex items-center gap-2 rounded-full px-6 py-2.5 font-semibold text-sm"
              style={{ background: C.forest, color: 'white' }}>
              <RefreshCw size={15} /> Reload Agricure
            </button>
          </div>
        </div>
      )
    }
    return this.props.children
  }
}
