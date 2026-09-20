import { createContext, useCallback, useContext, useMemo, useState } from 'react'
import { api, setAuthToken, setUnauthorizedHandler } from '../api/client.js'

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

  return (
    <AuthContext.Provider value={{ user, login, register, logout }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  return useContext(AuthContext)
}
