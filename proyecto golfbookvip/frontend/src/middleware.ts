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

  // Gate SSR: usa el flag NO sensible `gbv_authed` (Path=/), que SÍ es visible para el middleware.
  // NO usar `gbv_refresh` (Path=/api/v1/auth): no llega aquí y rebota al login en bucle.
  // Es un primer filtro; la auth real la impone el backend por request (Bearer) + los guards de cliente.
  if (!isPublic && !request.cookies.get('gbv_authed')) {
    return NextResponse.redirect(new URL(`/${locale}/auth/login`, request.url))
  }

  return NextResponse.next()
}

export const config = {
  matcher: ['/((?!api|_next|_vercel|.*\\..*).*)'],
}
