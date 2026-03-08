import { createContext, useContext, useState, useEffect, ReactNode } from 'react'
import { User, Task, Asset, Vulnerability } from '../types'
import { authAPI } from '../utils/api'

interface AppState {
  user: User | null
  tasks: Task[]
  assets: Asset[]
  vulnerabilities: Vulnerability[]
  loading: boolean
  error: string | null
}

interface AppActions {
  setUser: (user: User | null) => void
  fetchUser: () => Promise<void>
  setTasks: (tasks: Task[]) => void
  addTask: (task: Task) => void
  updateTask: (id: number, task: Partial<Task>) => void
  setAssets: (assets: Asset[]) => void
  setVulnerabilities: (vulnerabilities: Vulnerability[]) => void
  setLoading: (loading: boolean) => void
  setError: (error: string | null) => void
  clearError: () => void
}

interface StoreContextType {
  state: AppState
  actions: AppActions
}

const StoreContext = createContext<StoreContextType | undefined>(undefined)

export const StoreProvider = ({ children }: { children: ReactNode }) => {
  const [state, setState] = useState<AppState>({
    user: null,
    tasks: [],
    assets: [],
    vulnerabilities: [],
    loading: false,
    error: null,
  })

  const actions: AppActions = {
    setUser: (user) => setState(prev => ({ ...prev, user })),
    fetchUser: async () => {
      try {
        const user = await authAPI.getMe()
        setState(prev => ({ ...prev, user }))
      } catch (error) {
        console.error('Failed to fetch user:', error)
      }
    },
    setTasks: (tasks) => setState(prev => ({ ...prev, tasks })),
    addTask: (task) => setState(prev => ({ ...prev, tasks: [task, ...prev.tasks] })),
    updateTask: (id, taskUpdate) => setState(prev => ({
      ...prev,
      tasks: prev.tasks.map(t => t.id === id ? { ...t, ...taskUpdate } : t)
    })),
    setAssets: (assets) => setState(prev => ({ ...prev, assets })),
    setVulnerabilities: (vulnerabilities) => setState(prev => ({ ...prev, vulnerabilities })),
    setLoading: (loading) => setState(prev => ({ ...prev, loading })),
    setError: (error) => setState(prev => ({ ...prev, error })),
    clearError: () => setState(prev => ({ ...prev, error: null })),
  }

  // 初始化时获取用户信息
  useEffect(() => {
    const token = localStorage.getItem('token')
    if (token) {
      actions.fetchUser()
    }
  }, [])

  return (
    <StoreContext.Provider value={{ state, actions }}>
      {children}
    </StoreContext.Provider>
  )
}

export const useStore = (): StoreContextType => {
  const context = useContext(StoreContext)
  if (!context) {
    throw new Error('useStore must be used within StoreProvider')
  }
  return context
}
