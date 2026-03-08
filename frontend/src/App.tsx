import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { Suspense, lazy } from 'react'
import PrivateRoute from './components/PrivateRoute'
import MainLayout from './components/MainLayout'
import { StoreProvider } from './store'

// 立即加载的页面（登录/注册需要快速响应）
import Login from './pages/Login'
import Register from './pages/Register'

// 懒加载的页面（减少首屏 bundle 大小）
const Dashboard = lazy(() => import('./pages/Dashboard'))
const Tasks = lazy(() => import('./pages/Tasks'))
const TaskDetail = lazy(() => import('./pages/TaskDetail'))
const Domains = lazy(() => import('./pages/Domains'))
const Assets = lazy(() => import('./pages/Assets'))
const AssetDetail = lazy(() => import('./pages/AssetDetail'))
const AssetQuality = lazy(() => import('./pages/AssetQuality'))
const Vulnerabilities = lazy(() => import('./pages/Vulnerabilities'))
const VulnerabilityDetail = lazy(() => import('./pages/VulnerabilityDetail'))
const Credentials = lazy(() => import('./pages/Credentials'))
const ScanPlans = lazy(() => import('./pages/ScanPlans'))
const Fingerprints = lazy(() => import('./pages/Fingerprints'))
const Tools = lazy(() => import('./pages/Tools'))

// 页面加载占位符
const PageLoading = () => (
  <div style={{
    display: 'flex',
    justifyContent: 'center',
    alignItems: 'center',
    minHeight: '400px',
    color: '#64748B',
    fontSize: '14px'
  }}>
    <div style={{
      width: '40px',
      height: '40px',
      border: '3px solid rgba(14, 165, 233, 0.2)',
      borderTop: '3px solid #0EA5E9',
      borderRadius: '50%',
      animation: 'spin 1s linear infinite',
      marginRight: '12px'
    }} />
    加载中...
  </div>
)

function App() {
  return (
    <StoreProvider>
      <BrowserRouter>
        <Suspense fallback={<PageLoading />}>
          <Routes>
            <Route path="/login" element={<Login />} />
            <Route path="/register" element={<Register />} />
            <Route
              path="/"
              element={
                <PrivateRoute>
                  <MainLayout />
                </PrivateRoute>
              }
            >
              <Route index element={<Navigate to="/dashboard" replace />} />
              <Route path="dashboard" element={<Dashboard />} />
              <Route path="tasks" element={<Tasks />} />
              <Route path="tasks/:id" element={<TaskDetail />} />
              <Route path="domains" element={<Domains />} />
              <Route path="assets" element={<Assets />} />
              <Route path="assets/:id" element={<AssetDetail />} />
              <Route path="asset-quality" element={<AssetQuality />} />
              <Route path="vulnerabilities" element={<Vulnerabilities />} />
              <Route path="vulnerabilities/:id" element={<VulnerabilityDetail />} />
              <Route path="credentials" element={<Credentials />} />
              <Route path="scan-plans" element={<ScanPlans />} />
              <Route path="fingerprints" element={<Fingerprints />} />
              <Route path="tools" element={<Tools />} />
            </Route>
          </Routes>
        </Suspense>
      </BrowserRouter>
    </StoreProvider>
  )
}

export default App

