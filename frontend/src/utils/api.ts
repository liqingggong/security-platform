import axios from 'axios'
import type {
  User,
  UserCreate,
  UserLogin,
  Token,
  ApiCredential,
  CredentialUpdate,
  Task,
  TaskCreate,
  TaskUpdate,
  TaskLog,
  Asset,
  AssetListResponse,
  Vulnerability,
  VulnerabilityUpdate,
  ScanPlan,
  ScanPlanCreate,
  ScanPlanUpdate,
  FingerprintRule,
  FingerprintRuleCreate,
  FingerprintRuleUpdate,
  Tool,
  ToolUpdate,
  PaginationParams,
} from '../types'
import { setToken, setRefreshToken, removeTokens, getRefreshToken } from './auth'

const API_BASE_URL = '/api/v1'

let isRefreshing = false
let refreshSubscribers: Array<(token: string) => void> = []

const subscribeTokenRefresh = (callback: (token: string) => void) => {
  refreshSubscribers.push(callback)
}

const onRefreshed = (token: string) => {
  refreshSubscribers.forEach(callback => callback(token))
  refreshSubscribers = []
}

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
})

// 刷新 token 函数
const refreshAccessToken = async (): Promise<string> => {
  const refreshToken = getRefreshToken()
  if (!refreshToken) {
    throw new Error('No refresh token available')
  }

  const response = await axios.post(`${API_BASE_URL}/auth/refresh`, {
    refresh_token: refreshToken
  })

  const { access_token, refresh_token } = response.data
  setToken(access_token)
  setRefreshToken(refresh_token)
  return access_token
}

// 请求拦截器：添加 token
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('token')
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  (error) => {
    return Promise.reject(error)
  }
)

// 响应拦截器：处理错误和自动刷新 token
api.interceptors.response.use(
  (response) => {
    return response.data
  },
  async (error) => {
    const originalRequest = error.config

    // 如果是 401 错误且不是刷新请求
    if (error.response?.status === 401 && !originalRequest._retry && originalRequest.url !== '/auth/refresh') {
      if (isRefreshing) {
        // 如果正在刷新，将请求加入队列
        return new Promise((resolve) => {
          subscribeTokenRefresh((token: string) => {
            originalRequest.headers.Authorization = `Bearer ${token}`
            resolve(api(originalRequest))
          })
        })
      }

      isRefreshing = true

      try {
        // 尝试刷新 token
        const newToken = await refreshAccessToken()
        isRefreshing = false
        onRefreshed(newToken)

        // 重试原请求
        originalRequest.headers.Authorization = `Bearer ${newToken}`
        originalRequest._retry = true
        return api(originalRequest)
      } catch (refreshError) {
        isRefreshing = false
        // 刷新失败，清除所有 token
        removeTokens()
        error.isUnauthorized = true
        return Promise.reject(error)
      }
    }

    return Promise.reject(error)
  }
)

// 认证 API
export const authAPI = {
  register: (data: UserCreate): Promise<User> =>
    api.post('/auth/register', data),
  login: (data: UserLogin): Promise<Token> => {
    const formData = new FormData()
    formData.append('username', data.email)
    formData.append('password', data.password)
    return axios.post(`${API_BASE_URL}/auth/login`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    }).then(res => res.data)
  },
  refresh: () => api.post('/auth/refresh', {
    refresh_token: getRefreshToken() || ''
  }),
  getMe: (): Promise<User> => api.get('/auth/me'),
}

// 凭据 API
export const credentialsAPI = {
  list: (): Promise<ApiCredential[]> => api.get('/credentials'),
  get: (provider: string): Promise<ApiCredential> =>
    api.get(`/credentials/${provider}`),
  update: (provider: string, data: CredentialUpdate): Promise<ApiCredential> =>
    api.put(`/credentials/${provider}`, data),
}

// 任务 API
export const tasksAPI = {
  list: (params?: PaginationParams & { status?: string }): Promise<Task[]> =>
    api.get('/tasks', { params }),
  get: (id: number): Promise<Task> => api.get(`/tasks/${id}`),
  create: (data: TaskCreate): Promise<Task> => api.post('/tasks', data),
  update: (id: number, data: TaskUpdate): Promise<Task> =>
    api.patch(`/tasks/${id}`, data),
  cancel: (id: number): Promise<void> => api.delete(`/tasks/${id}`),
  deleteHard: (id: number): Promise<void> => api.delete(`/tasks/${id}/hard`),
  getLogs: (id: number, params?: { phase?: string }): Promise<TaskLog[]> =>
    api.get(`/tasks/${id}/logs`, { params }),
}

// 资产 API
export const assetsAPI = {
  list: (params?: PaginationParams & {
    type?: string
    task_id?: number
    search?: string
    view?: 'host' | 'service' | 'url'
    task_ids?: number[]
  }): Promise<AssetListResponse> =>
    api.get('/assets', { params }),
  get: (id: number): Promise<Asset> => api.get(`/assets/${id}`),
  getStats: () => api.get('/assets/stats/summary'),
  aggregate: (params: { view: 'host' | 'service' | 'url'; task_ids?: number[] }) =>
    api.get('/assets/aggregate', { params }),
}

// 漏洞 API
export const vulnerabilitiesAPI = {
  list: (params?: PaginationParams & {
    severity?: string
    status?: string
    task_id?: number
    asset_id?: number
    cve_id?: string
    search?: string
  }): Promise<Vulnerability[]> =>
    api.get('/vulnerabilities', { params }),
  get: (id: number): Promise<Vulnerability> => api.get(`/vulnerabilities/${id}`),
  update: (id: number, data: VulnerabilityUpdate): Promise<Vulnerability> =>
    api.patch(`/vulnerabilities/${id}`, data),
  getStats: () => api.get('/vulnerabilities/stats/summary'),
}

// 扫描方案 API
export const scanPlansAPI = {
  list: (): Promise<ScanPlan[]> => api.get('/scan-plans'),
  create: (data: ScanPlanCreate): Promise<ScanPlan> => api.post('/scan-plans', data),
  update: (id: number, data: ScanPlanUpdate): Promise<ScanPlan> =>
    api.put(`/scan-plans/${id}`, data),
  remove: (id: number): Promise<void> => api.delete(`/scan-plans/${id}`),
}

// 指纹规则 API
export const fingerprintRulesAPI = {
  list: (): Promise<FingerprintRule[]> => api.get('/fingerprints'),
  create: (data: FingerprintRuleCreate): Promise<FingerprintRule> =>
    api.post('/fingerprints', data),
  update: (id: number, data: FingerprintRuleUpdate): Promise<FingerprintRule> =>
    api.put(`/fingerprints/${id}`, data),
  remove: (id: number): Promise<void> => api.delete(`/fingerprints/${id}`),
}

// 工具管理 API
export const toolsAPI = {
  list: (): Promise<Tool[]> => api.get('/tools'),
  get: (id: number): Promise<Tool> => api.get(`/tools/${id}`),
  create: (formData: FormData): Promise<Tool> => {
    return axios.post(`${API_BASE_URL}/tools`, formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
        Authorization: `Bearer ${localStorage.getItem('token')}`,
      },
    }).then(res => res.data)
  },
  update: (id: number, data: ToolUpdate): Promise<Tool> =>
    api.put(`/tools/${id}`, data),
  remove: (id: number): Promise<void> => api.delete(`/tools/${id}`),
  toggle: (id: number, enabled: boolean): Promise<void> =>
    api.post(`/tools/${id}/toggle`, null, { params: { enabled } }),
}

export default api

