import axios, { AxiosError, InternalAxiosRequestConfig } from 'axios'

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'https://api.golfbookvip.com'

let accessToken: string | null = null
let refreshPromise: Promise<boolean> | null = null

type RetryConfig = InternalAxiosRequestConfig & { _retry?: boolean }

export const api = axios.create({
  baseURL: `${API_URL}/api/v1`,
  headers: { 'Content-Type': 'application/json' },
  withCredentials: true,
})

export function setAuth(token: string) {
  accessToken = token
  if (typeof window !== 'undefined') localStorage.setItem('gbv_authed', '1')
}

export function clearAuth() {
  accessToken = null
  if (typeof window !== 'undefined') localStorage.removeItem('gbv_authed')
}

export function isAuthed(): boolean {
  return typeof window !== 'undefined' && !!localStorage.getItem('gbv_authed')
}

export function getAccessToken(): string | null {
  return accessToken
}

export async function refreshAccessToken(): Promise<boolean> {
  if (refreshPromise) return refreshPromise
  refreshPromise = api.post('/auth/refresh')
    .then((res) => {
      const token = res.data?.access_token
      if (!token) {
        clearAuth()
        return false
      }
      setAuth(token)
      return true
    })
    .catch(() => {
      clearAuth()
      return false
    })
    .finally(() => {
      refreshPromise = null
    })
  return refreshPromise
}

function redirectToLogin() {
  if (typeof window === 'undefined') return
  const localeMatch = window.location.pathname.match(/^\/(es|en)/)
  const locale = localeMatch ? localeMatch[1] : 'es'
  window.location.href = `/${locale}/auth/login`
}

api.interceptors.request.use((config) => {
  if (accessToken) config.headers.Authorization = `Bearer ${accessToken}`
  return config
})

api.interceptors.response.use(
  (res) => res,
  async (err: AxiosError) => {
    const original = err.config as RetryConfig | undefined
    const url = original?.url ?? ''
    const isRefresh = url.includes('/auth/refresh')
    if (err.response?.status === 401 && original && !original._retry && !isRefresh) {
      original._retry = true
      const refreshed = await refreshAccessToken()
      if (refreshed) return api(original)
    }
    if (err.response?.status === 401 && typeof window !== 'undefined') {
      clearAuth()
      if (!isRefresh) redirectToLogin()
    }
    return Promise.reject(err)
  }
)
