import { NextRequest, NextResponse } from 'next/server'
import { locales, defaultLocale } from './lib/i18n'

export function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl
  const hasLocale = locales.some((l) => pathname.startsWith(`/${l}/`) || pathname === `/${l}`)
  if (!hasLocale) {
    return NextResponse.redirect(new URL(`/${defaultLocale}${pathname}`, request.url))
  }

  const locale = locales.find((l) => pathname === `/${l}` || pathname.startsWith(`/${l}/`)) ?? defaultLocale
  const pathWithoutLocale = pathname === `/${locale}` ? '/' : pathname.slice(`/${locale}`.length)
  const isPublic =
    pathWithoutLocale === '/' ||
    pathWithoutLocale.startsWith('/auth') ||
    pathWithoutLocale.startsWith('/join') ||
    pathWithoutLocale.startsWith('/join-club') ||
    pathWithoutLocale.startsWith('/live')

  if (!isPublic && !request.cookies.get('gbv_refresh')) {
    return NextResponse.redirect(new URL(`/${locale}/auth/login`, request.url))
  }

  return NextResponse.next()
}

export const config = {
  matcher: ['/((?!api|_next|_vercel|.*\\..*).*)'],
}
