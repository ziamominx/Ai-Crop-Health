import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react'
import { api, getAuthToken, setAuthToken, setUnauthorizedHandler } from '../api/client.js'

const AuthContext = createContext(null)

/* Authentication state lives in memory only — never localStorage (per security rules). */
export function AuthProvider({ children }) {
  const [user, setUser] = useState(null)

  const applySession = useCallback((data) => {
    setAuthToken(data.access_token)
    setUser(data.user)
    return data.user
  }, [])

  const login = useCallback(async (email, password) => {
    const data = await api.login(email, password)
    return applySession(data)
  }, [applySession])

  const register = useCallback(async (payload) => {
    const data = await api.register(payload)
    return applySession(data)
  }, [applySession])

  const logout = useCallback(() => {
    setAuthToken(null)
    setUser(null)
  }, [])

  // global 401 handling — drop the session
  useMemo(() => setUnauthorizedHandler(() => {
    setAuthToken(null)
    setUser(null)
  }), [])

  /* If a token was already set before React mounted (the static GitHub Pages demo
     restores its session from sessionStorage in main.jsx), pick the user back up.
     In the normal app no token exists at boot, so this is a no-op — sessions stay
     in memory only. */
  useEffect(() => {
    if (!getAuthToken()) return undefined
    let cancelled = false
    api.me()
      .then((me) => { if (!cancelled) setUser(me) })
      .catch(() => { setAuthToken(null) })
    return () => { cancelled = true }
  }, [])

  return (
    <AuthContext.Provider value={{ user, login, register, logout }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  return useContext(AuthContext)
}
