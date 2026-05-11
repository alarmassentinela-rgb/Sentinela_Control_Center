'use client'
import { useLocale } from '@/components/DictionaryProvider'
import { APP_VERSION } from '@/lib/version'

interface Props {
  className?: string
  align?: 'center' | 'left' | 'right'
}

export default function AleaCredit({ className = '', align = 'center' }: Props) {
  const locale = useLocale()
  const alignClass = align === 'center' ? 'text-center' : align === 'right' ? 'text-right' : 'text-left'
  return (
    <p className={`${alignClass} text-xs text-zinc-300 mt-8 ${className}`}>
      {locale === 'es' ? 'Desarrollado por' : 'Developed by'}{' '}
      <span className="text-emerald-400 font-semibold">AleaSystems</span>
      <span className="text-zinc-500 mx-1.5">·</span>
      <span className="text-emerald-400 font-mono">v{APP_VERSION}</span>
    </p>
  )
}
