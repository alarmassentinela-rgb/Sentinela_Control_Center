'use client'
import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import { Flag, ArrowLeft, Plus, Search, MapPin, Users, Loader2 } from 'lucide-react'
import { api } from '@/lib/api'
import { useLocale } from '@/components/DictionaryProvider'

interface Club {
  id: string
  name: string
  city: string | null
  country: string | null
  description: string | null
  member_count: number
  is_member: boolean
  role: string | null
}

export default function ClubsPage() {
  const locale = useLocale()
  const router = useRouter()
  const lbl = (es: string, en: string) => locale === 'es' ? es : en
  const [clubs, setClubs] = useState<Club[]>([])
  const [loading, setLoading] = useState(true)
  const [search, setSearch] = useState('')

  useEffect(() => {
    if (!localStorage.getItem('access_token')) { router.push(`/${locale}/auth/login`); return }
    fetchClubs()
  }, [])

  const fetchClubs = async (q = '') => {
    setLoading(true)
    try {
      const res = await api.get('/clubs', { params: q ? { search: q } : {} })
      setClubs(res.data)
    } finally {
      setLoading(false)
    }
  }

  const handleSearch = (e: React.FormEvent) => { e.preventDefault(); fetchClubs(search) }

  return (
    <div className="min-h-screen bg-zinc-950">
      <header className="bg-zinc-900 border-b border-zinc-800 px-4 py-4">
        <div className="max-w-4xl mx-auto flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Link href={`/${locale}/dashboard`} className="text-zinc-400 hover:text-white transition-colors">
              <ArrowLeft size={20} />
            </Link>
            <div className="flex items-center gap-2">
              <div className="w-7 h-7 rounded-full bg-emerald-500 flex items-center justify-center">
                <Flag size={14} className="text-white" />
              </div>
              <span className="font-bold text-white">GolfBook<span className="text-emerald-400">VIP</span></span>
            </div>
          </div>
          <Link href={`/${locale}/clubs/new`}
            className="flex items-center gap-2 bg-emerald-500 hover:bg-emerald-400 text-white text-sm font-semibold px-4 py-2 rounded-full transition-colors">
            <Plus size={16} />
            {lbl('Nuevo club', 'New club')}
          </Link>
        </div>
      </header>

      <main className="max-w-4xl mx-auto px-4 py-8">
        <h1 className="text-2xl font-bold text-white mb-6">{lbl('Clubs', 'Clubs')}</h1>

        <form onSubmit={handleSearch} className="flex gap-3 mb-6">
          <div className="relative flex-1">
            <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-zinc-500" />
            <input type="text" value={search} onChange={(e) => setSearch(e.target.value)}
              placeholder={lbl('Buscar club...', 'Search club...')}
              className="w-full bg-zinc-900 border border-zinc-800 rounded-xl pl-9 pr-4 py-2.5 text-white placeholder:text-zinc-600 focus:outline-none focus:border-emerald-500 transition-colors text-sm" />
          </div>
          <button type="submit" className="bg-zinc-800 hover:bg-zinc-700 text-white px-4 py-2.5 rounded-xl text-sm transition-colors">
            {lbl('Buscar', 'Search')}
          </button>
        </form>

        {loading ? (
          <div className="flex justify-center py-16"><Loader2 size={28} className="animate-spin text-emerald-500" /></div>
        ) : clubs.length === 0 ? (
          <div className="bg-zinc-900 border border-zinc-800 rounded-2xl p-12 text-center">
            <div className="w-14 h-14 rounded-full bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center mx-auto mb-4">
              <Users size={24} className="text-emerald-400" />
            </div>
            <h2 className="text-lg font-semibold text-white mb-2">{lbl('No hay clubs registrados', 'No clubs yet')}</h2>
            <p className="text-zinc-500 text-sm mb-5">{lbl('Crea el primer club de golf', 'Create the first golf club')}</p>
            <Link href={`/${locale}/clubs/new`}
              className="inline-flex items-center gap-2 bg-emerald-500 hover:bg-emerald-400 text-white font-semibold px-5 py-2.5 rounded-full transition-colors text-sm">
              <Plus size={16} />{lbl('Crear club', 'Create club')}
            </Link>
          </div>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            {clubs.map((c) => (
              <Link key={c.id} href={`/${locale}/clubs/${c.id}`}
                className="bg-zinc-900 border border-zinc-800 hover:border-emerald-500/40 rounded-2xl p-5 transition-all group">
                <div className="flex items-start justify-between mb-3">
                  <div className="w-10 h-10 rounded-xl bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center group-hover:bg-emerald-500/20 transition-colors">
                    <Users size={18} className="text-emerald-400" />
                  </div>
                  {c.is_member && (
                    <span className="text-xs bg-emerald-500/20 text-emerald-400 border border-emerald-500/30 px-2 py-0.5 rounded-full">
                      {c.role === 'owner' ? lbl('Fundador', 'Founder') : lbl('Miembro', 'Member')}
                    </span>
                  )}
                </div>
                <h3 className="font-semibold text-white mb-1">{c.name}</h3>
                {(c.city || c.country) && (
                  <div className="flex items-center gap-1 text-xs text-zinc-500 mb-2">
                    <MapPin size={12} />
                    {[c.city, c.country].filter(Boolean).join(', ')}
                  </div>
                )}
                {c.description && (
                  <p className="text-xs text-zinc-500 mb-3 line-clamp-2">{c.description}</p>
                )}
                <div className="flex items-center gap-1 text-xs text-zinc-500">
                  <Users size={12} />
                  {c.member_count} {lbl('miembros', 'members')}
                </div>
              </Link>
            ))}
          </div>
        )}
      </main>
    </div>
  )
}
