import { message } from 'antd'

export interface ApiError {
  response?: {
    status?: number
    data?: {
      detail?: string
      message?: string
    }
  }
  message?: string
  isUnauthorized?: boolean
}

export const handleApiError = (error: ApiError | any, defaultMessage: string = '操作失败'): string => {
  // 未授权错误
  if (error.isUnauthorized || error.response?.status === 401) {
    return '登录已过期，请重新登录'
  }

  // 服务器错误
  if (error.response?.status === 500) {
    return '服务器错误，请稍后重试'
  }

  // 网络错误
  if (!error.response && error.message) {
    return '网络错误，请检查网络连接'
  }

  // 获取服务器返回的错误消息
  const serverMessage = error.response?.data?.detail || error.response?.data?.message

  if (serverMessage) {
    return serverMessage
  }

  // 使用默认消息
  return defaultMessage
}

export const showError = (error: ApiError | any, defaultMessage: string = '操作失败') => {
  const errorMessage = handleApiError(error, defaultMessage)
  message.error(errorMessage)
}

export const showSuccess = (msg: string) => {
  message.success(msg)
}

export const showWarning = (msg: string) => {
  message.warning(msg)
}

export const showInfo = (msg: string) => {
  message.info(msg)
}
