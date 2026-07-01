'use client'

import { useEffect } from 'react'
import { refreshAccessToken } from '@/lib/api'

export default function AuthBootstrap() {
  useEffect(() => {
    refreshAccessToken()
  }, [])

  return null
}
