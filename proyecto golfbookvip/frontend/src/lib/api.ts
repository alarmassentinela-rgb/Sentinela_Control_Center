import axios from 'axios'

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'https://api.golfbookvip.com'

export const api = axios.create({
  baseURL: `${API_URL}/api/v1`,
  headers: { 'Content-Type': 'application/json' },
})

api.interceptors.request.use((config) => {
  if (typeof window !== 'undefined') {
    const token = localStorage.getItem('access_token')
    if (token) config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

api.interceptors.response.use(
  (res) => res,
  (err) => {
    if (err.response?.status === 401 && typeof window !== 'undefined') {
      localStorage.removeItem('access_token')
      const localeMatch = window.location.pathname.match(/^\/(es|en)/)
      const locale = localeMatch ? localeMatch[1] : 'es'
      window.location.href = `/${locale}/auth/login`
    }
    return Promise.reject(err)
  }
)
