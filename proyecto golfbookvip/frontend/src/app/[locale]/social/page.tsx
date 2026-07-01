'use client'
import { useEffect, useState, useCallback } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import { ArrowLeft, Search, UserPlus, UserMinus, Loader2, Users } from 'lucide-react'
import { api, isAuthed } from '@/lib/api'
import { useLocale } from '@/components/DictionaryProvider'

interface UserResult {
  id: string
  username: string
  first_name: string
  last_name: string
  handicap_index: number | null
}

export default function SocialPage() {
  const locale = useLocale()
  const router = useRouter()
  const lbl = (es: string, en: string) => locale === 'es' ? es : en

  const [query, setQuery] = useState('')
  const [results, setResults] = useState<UserResult[]>([])
  const [following, setFollowing] = useState<UserResult[]>([])
  const [followingIds, setFollowingIds] = useState<Set<string>>(new Set())
  const [searching, setSearching] = useState(false)
  const [loadingFollow, setLoadingFollow] = useState<string | null>(null)
  const [searchDone, setSearchDone] = useState(false)

  useEffect(() => {
    const token = isAuthed()
    if (!token) { router.push(`/${locale}/auth/login`); return }
    api.get('/users/me/following')
      .then(r => {
        setFollowing(r.data)
        setFollowingIds(new Set(r.data.map((u: UserResult) => u.id)))
      })
      .catch(() => {})
  }, [locale, router])

  const doSearch = useCallback(async (q: string) => {
    if (q.trim().length < 2) { setResults([]); setSearchDone(false); return }
    setSearching(true)
    try {
      const r = await api.get(`/users/search?q=${encodeURIComponent(q.trim())}`)
      setResults(r.data)
      setSearchDone(true)
    } catch {
      setResults([])
    } finally {
      setSearching(false)
    }
  }, [])

  useEffect(() => {
    const t = setTimeout(() => doSearch(query), 400)
    return () => clearTimeout(t)
  }, [query, doSearch])

  const toggleFollow = async (user: UserResult) => {
    setLoadingFollow(user.id)
    try {
      if (followingIds.has(user.id)) {
        await api.delete(`/users/${user.id}/follow`)
        setFollowingIds(prev => { const s = new Set(prev); s.delete(user.id); return s })
        setFollowing(prev => prev.filter(u => u.id !== user.id))
      } else {
        await api.post(`/users/${user.id}/follow`)
        setFollowingIds(prev => new Set([...prev, user.id]))
        setFollowing(prev => [...prev, user])
      }
    } catch {
    } finally {
      setLoadingFollow(null)
    }
  }

  const UserCard = ({ user, showFollowBtn = true }: { user: UserResult; showFollowBtn?: boolean }) => {
    const isFollowing = followingIds.has(user.id)
    const isLoading = loadingFollow === user.id
    return (
      <div className="flex items-center gap-3 py-3 px-4">
        <div className="w-10 h-10 rounded-full bg-emerald-500/20 border border-emerald-500/30 flex items-center justify-center flex-shrink-0">
          <span className="text-sm font-bold text-emerald-400">{user.first_name[0]}{user.last_name[0]}</span>
        </div>
        <div className="flex-1 min-w-0">
          <p className="text-sm font-semibold text-white">{user.first_name} {user.last_name}</p>
          <p className="text-xs text-zinc-500">
            @{user.username}
            {user.handicap_index != null && ` · HCP ${user.handicap_index.toFixed(1)}`}
          </p>
        </div>
        {showFollowBtn && (
          <button
            onClick={() => toggleFollow(user)}
            disabled={isLoading}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold border transition-all disabled:opacity-50 ${
              isFollowing
                ? 'bg-zinc-800 border-zinc-700 text-zinc-300 hover:bg-red-500/10 hover:border-red-500/30 hover:text-red-400'
                : 'bg-emerald-500/10 border-emerald-500/30 text-emerald-400 hover:bg-emerald-500/20'
            }`}>
            {isLoading
              ? <Loader2 size={12} className="animate-spin" />
              : isFollowing
                ? <><UserMinus size={12} />{lbl('Siguiendo', 'Following')}</>
                : <><UserPlus size={12} />{lbl('Seguir', 'Follow')}</>
            }
          </button>
        )}
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-zinc-950">
      <header className="bg-zinc-900 border-b border-zinc-800 px-4 py-4 sticky top-0 z-10">
        <div className="max-w-xl mx-auto flex items-center gap-3">
          <Link href={`/${locale}/dashboard`} className="text-zinc-400 hover:text-white transition-colors">
            <ArrowLeft size={20} />
          </Link>
          <h1 className="font-bold text-white text-lg flex-1">
            {lbl('Jugadores', 'Players')}
          </h1>
          <Link href={`/${locale}/groups`}
            className="flex items-center gap-1.5 text-xs text-emerald-400 hover:text-emerald-300 transition-colors">
            <Users size={15} />
            {lbl('Mis grupos', 'My groups')}
          </Link>
        </div>
      </header>

      <main className="max-w-xl mx-auto px-4 py-6 space-y-6">
        {/* Search */}
        <div className="relative">
          <Search size={16} className="absolute left-3.5 top-1/2 -translate-y-1/2 text-zinc-500" />
          <input
            type="text"
            value={query}
            onChange={e => setQuery(e.target.value)}
            placeholder={lbl('Buscar por nombre o usuario…', 'Search by name or username…')}
            className="w-full bg-zinc-900 border border-zinc-800 rounded-xl pl-10 pr-4 py-3 text-sm text-white placeholder:text-zinc-600 focus:outline-none focus:border-emerald-500 transition-colors"
          />
          {searching && (
            <Loader2 size={14} className="absolute right-3.5 top-1/2 -translate-y-1/2 text-zinc-500 animate-spin" />
          )}
        </div>

        {/* Search results */}
        {query.trim().length >= 2 && (
          <div className="bg-zinc-900 border border-zinc-800 rounded-2xl overflow-hidden">
            <div className="px-4 py-3 border-b border-zinc-800">
              <p className="text-xs font-semibold text-zinc-500 uppercase tracking-wide">
                {lbl('Resultados', 'Results')}
              </p>
            </div>
            {results.length === 0 && searchDone ? (
              <p className="text-sm text-zinc-500 text-center py-8">
                {lbl('Sin resultados para', 'No results for')} "{query}"
              </p>
            ) : (
              <div className="divide-y divide-zinc-800">
                {results.map(u => <UserCard key={u.id} user={u} />)}
              </div>
            )}
          </div>
        )}

        {/* Following list */}
        <div className="bg-zinc-900 border border-zinc-800 rounded-2xl overflow-hidden">
          <div className="px-4 py-3 border-b border-zinc-800">
            <p className="text-xs font-semibold text-zinc-500 uppercase tracking-wide">
              {lbl('Siguiendo', 'Following')} · {following.length}
            </p>
          </div>
          {following.length === 0 ? (
            <div className="py-10 text-center px-4">
              <UserPlus size={28} className="text-zinc-700 mx-auto mb-3" />
              <p className="text-sm text-zinc-500">
                {lbl('Todavía no sigues a nadie. Búscalos arriba.', 'You\'re not following anyone yet. Search above.')}
              </p>
            </div>
          ) : (
            <div className="divide-y divide-zinc-800">
              {following.map(u => <UserCard key={u.id} user={u} />)}
            </div>
          )}
        </div>
      </main>
    </div>
  )
}
