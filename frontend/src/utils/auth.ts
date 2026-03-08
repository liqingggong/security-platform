export const setToken = (token: string) => {
  localStorage.setItem('token', token)
}

export const getToken = (): string | null => {
  return localStorage.getItem('token')
}

export const setRefreshToken = (token: string) => {
  localStorage.setItem('refresh_token', token)
}

export const getRefreshToken = (): string | null => {
  return localStorage.getItem('refresh_token')
}

export const removeToken = () => {
  localStorage.removeItem('token')
}

export const removeRefreshToken = () => {
  localStorage.removeItem('refresh_token')
}

export const removeTokens = () => {
  removeToken()
  removeRefreshToken()
}

export const isAuthenticated = (): boolean => {
  return !!getToken()
}

export const hasRefreshToken = (): boolean => {
  return !!getRefreshToken()
}

