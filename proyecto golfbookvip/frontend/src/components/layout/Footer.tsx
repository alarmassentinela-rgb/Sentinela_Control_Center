'use client'
import { Flag } from 'lucide-react'
import { useT, useLocale } from '@/components/DictionaryProvider'
import { APP_VERSION } from '@/lib/version'

export default function Footer() {
  const t = useT('footer')
  const locale = useLocale()

  return (
    <footer className="bg-zinc-950 border-t border-zinc-800 py-12 px-4">
      <div className="max-w-7xl mx-auto">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-8 mb-8">
          <div>
            <div className="flex items-center gap-2 mb-3">
              <div className="w-7 h-7 rounded-full bg-emerald-500 flex items-center justify-center">
                <Flag size={14} className="text-white" />
              </div>
              <span className="font-bold text-white">GolfBook<span className="text-emerald-400">VIP</span></span>
            </div>
            <p className="text-sm text-zinc-500 max-w-xs">{t('tagline')}</p>
          </div>

          <div>
            <h4 className="text-sm font-semibold text-zinc-300 mb-3">
              {locale === 'es' ? 'Navegación' : 'Navigation'}
            </h4>
            <ul className="space-y-2 text-sm text-zinc-500">
              <li><a href={`/${locale}#features`} className="hover:text-zinc-300 transition-colors">
                {locale === 'es' ? 'Funciones' : 'Features'}
              </a></li>
              <li><a href={`/${locale}/auth/login`} className="hover:text-zinc-300 transition-colors">
                {locale === 'es' ? 'Iniciar sesión' : 'Log in'}
              </a></li>
              <li><a href={`/${locale}/auth/register`} className="hover:text-zinc-300 transition-colors">
                {locale === 'es' ? 'Registrarse' : 'Sign up'}
              </a></li>
            </ul>
          </div>

          <div>
            <h4 className="text-sm font-semibold text-zinc-300 mb-3">{t('developed')}</h4>
            <div className="flex items-center gap-2">
              <div className="w-8 h-8 rounded bg-emerald-500/20 border border-emerald-500/30 flex items-center justify-center">
                <span className="text-emerald-400 font-bold text-xs">A</span>
              </div>
              <div>
                <p className="text-sm font-semibold text-white">AleaSystems</p>
                <p className="text-xs text-zinc-500">aleasystems.io</p>
              </div>
            </div>
          </div>
        </div>

        <div className="border-t border-zinc-800 pt-6 flex flex-col sm:flex-row items-center justify-between gap-2 text-xs text-zinc-400">
          <p>© {new Date().getFullYear()} GolfBookVIP. {t('rights')}</p>
          <p>
            {t('developed')}{' '}
            <span className="text-emerald-400 font-semibold">AleaSystems</span>
            <span className="text-zinc-500 mx-1.5">·</span>
            <span className="text-emerald-400 font-mono">v{APP_VERSION}</span>
          </p>
        </div>
      </div>
    </footer>
  )
}
