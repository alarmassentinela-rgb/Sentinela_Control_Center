import type { Metadata, Viewport } from 'next'
import Script from 'next/script'
import { Geist } from 'next/font/google'
import { notFound } from 'next/navigation'
import { locales, type Locale, getDictionary } from '@/lib/i18n'
import { DictionaryProvider } from '@/components/DictionaryProvider'
import BackgroundProvider from '@/components/BackgroundProvider'
import AuthBootstrap from '@/components/AuthBootstrap'
import ServiceWorkerRegistration from '@/components/ServiceWorkerRegistration'
import ChatWidget from '@/components/ChatWidget'
import SunModeToggle from '@/components/SunModeToggle'
import '../globals.css'

const geist = Geist({ subsets: ['latin'], variable: '--font-geist' })

export const viewport: Viewport = {
  themeColor: '#10b981',
  width: 'device-width',
  initialScale: 1,
  maximumScale: 1,
  userScalable: false,
}

export const metadata: Metadata = {
  title: 'GolfBookVIP — Tu compañero de golf',
  description: 'Scorecard digital, hándicap WHS, apuestas y estadísticas para golfistas.',
  manifest: '/manifest.json',
  appleWebApp: {
    capable: true,
    statusBarStyle: 'black-translucent',
    title: 'GolfBookVIP',
  },
  icons: {
    icon: [
      { url: '/icons/icon-192.png', sizes: '192x192', type: 'image/png' },
      { url: '/icons/icon-512.png', sizes: '512x512', type: 'image/png' },
    ],
    apple: [
      { url: '/icons/apple-touch-icon.png', sizes: '180x180', type: 'image/png' },
    ],
  },
  other: {
    'mobile-web-app-capable': 'yes',
    'application-name': 'GolfBookVIP',
    'msapplication-TileColor': '#10b981',
    'msapplication-tap-highlight': 'no',
  },
}

export default async function LocaleLayout({
  children,
  params,
}: {
  children: React.ReactNode
  params: Promise<{ locale: string }>
}) {
  const { locale } = await params
  if (!locales.includes(locale as Locale)) notFound()

  const dict = getDictionary(locale as Locale)

  return (
    <html lang={locale} className={`${geist.variable} h-full antialiased`}>
      <body className="min-h-full flex flex-col text-zinc-100">
        {/* Anti-flash: aplica Modo Sol antes del primer pintado si el usuario lo dejó activo */}
        <Script id="gbv-sun-mode-init" strategy="beforeInteractive">
          {`try{if(localStorage.getItem('gbv-sun-mode')==='1'){document.documentElement.setAttribute('data-theme','sun')}}catch(e){}`}
        </Script>
        <DictionaryProvider dict={dict} locale={locale as Locale}>
          <AuthBootstrap />
          <BackgroundProvider>
            {children}
          </BackgroundProvider>
        </DictionaryProvider>
        <SunModeToggle />
        <ChatWidget />
        <ServiceWorkerRegistration />
      </body>
    </html>
  )
}
