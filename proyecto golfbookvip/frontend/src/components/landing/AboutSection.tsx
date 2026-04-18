'use client'
import { useLocale } from '@/components/DictionaryProvider'

export default function AboutSection() {
  const locale = useLocale()
  return (
    <section id="about" className="py-24 px-4 bg-gradient-to-b from-zinc-950 to-zinc-900">
      <div className="max-w-4xl mx-auto text-center">
        <div className="inline-flex items-center gap-3 bg-zinc-800 border border-zinc-700 rounded-2xl px-6 py-4 mb-8">
          <div className="w-10 h-10 rounded-lg bg-emerald-500/20 border border-emerald-500/30 flex items-center justify-center">
            <span className="text-emerald-400 font-bold text-lg">A</span>
          </div>
          <div className="text-left">
            <p className="text-white font-bold">AleaSystems</p>
            <p className="text-zinc-400 text-sm">aleasystems.io</p>
          </div>
        </div>
        <h2 className="text-3xl font-bold text-white mb-4">
          {locale === 'es' ? 'Desarrollado por AleaSystems' : 'Developed by AleaSystems'}
        </h2>
        <p className="text-zinc-400 text-lg max-w-2xl mx-auto">
          {locale === 'es'
            ? 'AleaSystems es una empresa de desarrollo de software especializada en soluciones tecnológicas innovadoras. GolfBookVIP es nuestra plataforma de golf de próxima generación.'
            : 'AleaSystems is a software development company specialized in innovative technology solutions. GolfBookVIP is our next-generation golf platform.'}
        </p>
      </div>
    </section>
  )
}
