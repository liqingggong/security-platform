import { Navigate } from 'react-router-dom'
import { isAuthenticated } from '../utils/auth'

interface PrivateRouteProps {
  children: React.ReactNode
}

const PrivateRoute = ({ children }: PrivateRouteProps) => {
  if (!isAuthenticated()) {
    return <Navigate to="/login" replace />
  }
  return <>{children}</>
}

export default PrivateRoute

