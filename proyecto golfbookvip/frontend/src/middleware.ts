import { NextRequest, NextResponse } from 'next/server'
import { locales, defaultLocale } from './lib/i18n'

export function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl
  const hasLocale = locales.some((l) => pathname.startsWith(`/${l}/`) || pathname === `/${l}`)
  if (!hasLocale) {
    return NextResponse.redirect(new URL(`/${defaultLocale}${pathname}`, request.url))
  }

  // La protección de rutas se hace en cliente (isAuthed) + backend (auth por request).
  // NO se hace gate SSR por cookie aquí: la cookie de refresh (gbv_refresh) está scoped a
  // Path=/api/v1/auth y NO es visible para el middleware del frontend, por lo que un gate
  // basado en su presencia rebota al login en bucle incluso con sesión válida.
  return NextResponse.next()
}

export const config = {
  matcher: ['/((?!api|_next|_vercel|.*\\..*).*)'],
}
