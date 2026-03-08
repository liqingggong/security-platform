import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import PrivateRoute from './components/PrivateRoute'
import Login from './pages/Login'
import Register from './pages/Register'
import Dashboard from './pages/Dashboard'
import Tasks from './pages/Tasks'
import TaskDetail from './pages/TaskDetail'
import Domains from './pages/Domains'
import Assets from './pages/Assets'
import AssetDetail from './pages/AssetDetail'
import AssetQuality from './pages/AssetQuality'
import Vulnerabilities from './pages/Vulnerabilities'
import VulnerabilityDetail from './pages/VulnerabilityDetail'
import Credentials from './pages/Credentials'
import ScanPlans from './pages/ScanPlans'
import Fingerprints from './pages/Fingerprints'
import Tools from './pages/Tools'
import MainLayout from './components/MainLayout'
import { StoreProvider } from './store'

function App() {
  return (
    <StoreProvider>
      <BrowserRouter>
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
      </BrowserRouter>
    </StoreProvider>
  )
}

export default App

