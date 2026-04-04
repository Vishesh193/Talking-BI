import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import axios from 'axios'

interface User {
  user_id: string
  email: string
  role: string
  permitted_sources: string[]
}

interface AuthState {
  user: User | null
  token: string | null
  isAuthenticated: boolean
  login: (token: string, user: User) => void
  logout: () => void
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      user: null,
      token: null,
      isAuthenticated: false,
      login: (token, user) => {
        set({ token, user, isAuthenticated: true })
        axios.defaults.headers.common['Authorization'] = `Bearer ${token}`
      },
      logout: () => {
        set({ token: null, user: null, isAuthenticated: false })
        delete axios.defaults.headers.common['Authorization']
      },
    }),
    { name: 'talking-bi-auth' }
  )
)
