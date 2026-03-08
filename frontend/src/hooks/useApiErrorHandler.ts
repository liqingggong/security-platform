import { useEffect } from 'react'
import { useNavigate } from 'react-router-dom'

interface ApiError extends Error {
  response?: {
    status?: number
    data?: any
  }
  isUnauthorized?: boolean
}

export const useApiErrorHandler = () => {
  const navigate = useNavigate()

  useEffect(() => {
    const handleApiError = (event: Event) => {
      const errorEvent = event as CustomEvent<ApiError>
      const error = errorEvent.detail

      if (error.isUnauthorized || error.response?.status === 401) {
        navigate('/login', { replace: true })
      }
    }

    window.addEventListener('api-error', handleApiError)

    return () => {
      window.removeEventListener('api-error', handleApiError)
    }
  }, [navigate])

  const handleApiCall = async <T>(
    apiCall: () => Promise<T>
  ): Promise<T> => {
    try {
      return await apiCall()
    } catch (error: any) {
      if (error.isUnauthorized || error.response?.status === 401) {
        navigate('/login', { replace: true })
        throw error
      }
      throw error
    }
  }

  return { handleApiCall }
}
