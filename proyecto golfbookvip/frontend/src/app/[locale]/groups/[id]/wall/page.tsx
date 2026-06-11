'use client'
import { useEffect, useState, useCallback } from 'react'
import { useRouter, useParams } from 'next/navigation'
import Link from 'next/link'
import { ArrowLeft, Heart, MessageCircle, Trash2, Send, Loader2, MessagesSquare } from 'lucide-react'
import { api } from '@/lib/api'
import { useLocale } from '@/components/DictionaryProvider'

interface Author { user_id: string; username: string; first_name: string; last_name: string }
interface Post {
  id: string
  content: string
  author: Author
  is_pinned: boolean
  reactions_count: number
  comments_count: number
  liked_by_me: boolean
  created_at: string | null
  can_delete: boolean
}
interface Comment {
  id: string
  content: string
  author: Author
  created_at: string | null
  can_delete: boolean
}

function timeAgo(iso: string | null, locale: string): string {
  if (!iso) return ''
  const d = new Date(iso).getTime()
  const s = Math.floor((Date.now() - d) / 1000)
  const es = locale === 'es'
  if (s < 60) return es ? 'ahora' : 'now'
  const m = Math.floor(s / 60)
  if (m < 60) return `${m}m`
  const h = Math.floor(m / 60)
  if (h < 24) return `${h}h`
  const days = Math.floor(h / 24)
  if (days < 7) return `${days}${es ? 'd' : 'd'}`
  return new Date(iso).toLocaleDateString(es ? 'es-MX' : 'en-US', { day: 'numeric', month: 'short' })
}

function initials(a: Author) { return `${a.first_name?.[0] ?? ''}${a.last_name?.[0] ?? ''}` }

export default function GroupWallPage() {
  const locale = useLocale()
  const router = useRouter()
  const params = useParams()
  const groupId = params.id as string
  const lbl = (es: string, en: string) => locale === 'es' ? es : en

  const [groupName, setGroupName] = useState('')
  const [posts, setPosts] = useState<Post[]>([])
  const [loading, setLoading] = useState(true)
  const [draft, setDraft] = useState('')
  const [posting, setPosting] = useState(false)
  const [openComments, setOpenComments] = useState<string | null>(null)

  const load = useCallback(() => {
    return Promise.all([
      api.get(`/groups/${groupId}`),
      api.get(`/groups/${groupId}/posts`),
    ]).then(([g, p]) => {
      setGroupName(g.data.name)
      setPosts(p.data || [])
    })
  }, [groupId])

  useEffect(() => {
    const token = localStorage.getItem('access_token')
    if (!token) { router.push(`/${locale}/auth/login`); return }
    load().catch(() => router.push(`/${locale}/groups/${groupId}`)).finally(() => setLoading(false))
  }, [groupId, locale, router, load])

  const submitPost = async () => {
    const content = draft.trim()
    if (!content) return
    setPosting(true)
    try {
      const res = await api.post(`/groups/${groupId}/posts`, { content })
      setPosts(prev => [res.data, ...prev])
      setDraft('')
    } catch (e: unknown) {
      const detail = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail
      alert(detail ?? lbl('Error al publicar', 'Error posting'))
    } finally {
      setPosting(false)
    }
  }

  const toggleLike = async (post: Post) => {
    // optimistic
    setPosts(prev => prev.map(p => p.id === post.id
      ? { ...p, liked_by_me: !p.liked_by_me, reactions_count: p.reactions_count + (p.liked_by_me ? -1 : 1) }
      : p))
    try {
      const res = await api.post(`/groups/${groupId}/posts/${post.id}/react`)
      setPosts(prev => prev.map(p => p.id === post.id
        ? { ...p, liked_by_me: res.data.liked, reactions_count: res.data.reactions_count } : p))
    } catch {
      load() // revert via reload on error
    }
  }

  const deletePost = async (postId: string) => {
    if (!confirm(lbl('¿Borrar esta publicación?', 'Delete this post?'))) return
    setPosts(prev => prev.filter(p => p.id !== postId))
    try {
      await api.delete(`/groups/${groupId}/posts/${postId}`)
    } catch {
      load()
    }
  }

  if (loading) return (
    <div className="min-h-screen bg-zinc-950 flex items-center justify-center">
      <div className="w-8 h-8 border-2 border-emerald-500 border-t-transparent rounded-full animate-spin" />
    </div>
  )

  return (
    <div className="min-h-screen bg-zinc-950">
      <header className="bg-zinc-900 border-b border-zinc-800 px-4 py-4 sticky top-0 z-10">
        <div className="max-w-xl mx-auto flex items-center gap-3">
          <Link href={`/${locale}/groups/${groupId}`} className="text-zinc-400 hover:text-white transition-colors">
            <ArrowLeft size={20} />
          </Link>
          <div className="flex items-center gap-2 flex-1 min-w-0">
            <MessagesSquare size={18} className="text-emerald-400 flex-shrink-0" />
            <div className="min-w-0">
              <h1 className="font-bold text-white text-lg truncate">{lbl('Muro', 'Wall')}</h1>
              <p className="text-xs text-zinc-500 truncate">{groupName}</p>
            </div>
          </div>
        </div>
      </header>

      <main className="max-w-xl mx-auto px-4 py-5 space-y-4">
        {/* Composer */}
        <div className="bg-zinc-900 border border-zinc-800 rounded-2xl p-4">
          <textarea
            value={draft}
            onChange={e => setDraft(e.target.value)}
            maxLength={2000}
            rows={3}
            placeholder={lbl('Escribe algo para el grupo…', 'Write something for the group…')}
            className="w-full bg-zinc-950 border border-zinc-800 rounded-xl px-3 py-2.5 text-sm text-white placeholder-zinc-600 focus:outline-none focus:border-emerald-500/50 resize-none"
          />
          <div className="flex items-center justify-between mt-2">
            <span className="text-xs text-zinc-600">{draft.length}/2000</span>
            <button onClick={submitPost} disabled={posting || !draft.trim()}
              className="flex items-center gap-1.5 px-4 py-2 bg-emerald-500 hover:bg-emerald-400 disabled:opacity-50 disabled:cursor-not-allowed text-white rounded-xl text-sm font-semibold transition-colors">
              {posting ? <Loader2 size={14} className="animate-spin" /> : <Send size={14} />}
              {lbl('Publicar', 'Post')}
            </button>
          </div>
        </div>

        {/* Posts */}
        {posts.length === 0 ? (
          <div className="bg-zinc-900 border border-zinc-800 rounded-2xl px-5 py-10 text-center">
            <MessagesSquare size={24} className="text-zinc-700 mx-auto mb-2" />
            <p className="text-sm text-zinc-500">{lbl('Sé el primero en publicar en el grupo.', 'Be the first to post in the group.')}</p>
          </div>
        ) : posts.map(post => (
          <article key={post.id} className="bg-zinc-900 border border-zinc-800 rounded-2xl p-4">
            <div className="flex items-center gap-3 mb-2">
              <div className="w-9 h-9 rounded-full bg-zinc-800 border border-zinc-700 flex items-center justify-center flex-shrink-0">
                <span className="text-xs font-bold text-zinc-400">{initials(post.author)}</span>
              </div>
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium text-white truncate">{post.author.first_name} {post.author.last_name}</p>
                <p className="text-xs text-zinc-500">@{post.author.username} · {timeAgo(post.created_at, locale)}</p>
              </div>
              {post.can_delete && (
                <button onClick={() => deletePost(post.id)} className="p-1.5 text-zinc-600 hover:text-red-400 transition-colors">
                  <Trash2 size={14} />
                </button>
              )}
            </div>
            <p className="text-sm text-zinc-200 whitespace-pre-wrap break-words mb-3">{post.content}</p>
            <div className="flex items-center gap-4 text-sm">
              <button onClick={() => toggleLike(post)}
                className={`flex items-center gap-1.5 transition-colors ${post.liked_by_me ? 'text-red-400' : 'text-zinc-500 hover:text-red-400'}`}>
                <Heart size={16} className={post.liked_by_me ? 'fill-current' : ''} />
                {post.reactions_count > 0 && <span className="text-xs">{post.reactions_count}</span>}
              </button>
              <button onClick={() => setOpenComments(openComments === post.id ? null : post.id)}
                className="flex items-center gap-1.5 text-zinc-500 hover:text-emerald-400 transition-colors">
                <MessageCircle size={16} />
                {post.comments_count > 0 && <span className="text-xs">{post.comments_count}</span>}
              </button>
            </div>
            {openComments === post.id && (
              <CommentThread groupId={groupId} postId={post.id} locale={locale}
                onCountChange={(delta) => setPosts(prev => prev.map(p => p.id === post.id ? { ...p, comments_count: Math.max(0, p.comments_count + delta) } : p))} />
            )}
          </article>
        ))}
      </main>
    </div>
  )
}

function CommentThread({ groupId, postId, locale, onCountChange }: {
  groupId: string; postId: string; locale: string; onCountChange: (delta: number) => void
}) {
  const lbl = (es: string, en: string) => locale === 'es' ? es : en
  const [comments, setComments] = useState<Comment[] | null>(null)
  const [draft, setDraft] = useState('')
  const [sending, setSending] = useState(false)

  useEffect(() => {
    api.get(`/groups/${groupId}/posts/${postId}/comments`).then(r => setComments(r.data || [])).catch(() => setComments([]))
  }, [groupId, postId])

  const send = async () => {
    const content = draft.trim()
    if (!content) return
    setSending(true)
    try {
      const res = await api.post(`/groups/${groupId}/posts/${postId}/comments`, { content })
      setComments(prev => [...(prev ?? []), res.data])
      setDraft('')
      onCountChange(1)
    } catch {
      alert(lbl('Error al comentar', 'Error commenting'))
    } finally {
      setSending(false)
    }
  }

  return (
    <div className="mt-3 pt-3 border-t border-zinc-800 space-y-3">
      {comments === null ? (
        <div className="flex justify-center py-2"><Loader2 size={16} className="animate-spin text-zinc-600" /></div>
      ) : comments.map(c => (
        <div key={c.id} className="flex items-start gap-2.5">
          <div className="w-7 h-7 rounded-full bg-zinc-800 border border-zinc-700 flex items-center justify-center flex-shrink-0 mt-0.5">
            <span className="text-[10px] font-bold text-zinc-400">{initials(c.author)}</span>
          </div>
          <div className="flex-1 min-w-0">
            <p className="text-xs text-zinc-400">
              <span className="font-medium text-zinc-200">{c.author.first_name} {c.author.last_name}</span>
              {' · '}{timeAgo(c.created_at, locale)}
            </p>
            <p className="text-sm text-zinc-300 whitespace-pre-wrap break-words">{c.content}</p>
          </div>
        </div>
      ))}
      <div className="flex items-center gap-2">
        <input value={draft} onChange={e => setDraft(e.target.value)} maxLength={1000}
          onKeyDown={e => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); send() } }}
          placeholder={lbl('Escribe un comentario…', 'Write a comment…')}
          className="flex-1 bg-zinc-950 border border-zinc-800 rounded-xl px-3 py-2 text-sm text-white placeholder-zinc-600 focus:outline-none focus:border-emerald-500/50" />
        <button onClick={send} disabled={sending || !draft.trim()}
          className="p-2 bg-emerald-500/15 border border-emerald-500/30 text-emerald-300 hover:bg-emerald-500/25 disabled:opacity-50 rounded-xl transition-colors">
          {sending ? <Loader2 size={15} className="animate-spin" /> : <Send size={15} />}
        </button>
      </div>
    </div>
  )
}
