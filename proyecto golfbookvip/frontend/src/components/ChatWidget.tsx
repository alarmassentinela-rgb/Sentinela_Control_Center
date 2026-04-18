'use client'
import { useState, useRef, useEffect, useCallback } from 'react'
import { usePathname } from 'next/navigation'
import { MessageCircle, X, Send, Loader2, Bot, User, Trash2 } from 'lucide-react'
import { useLocale } from '@/components/DictionaryProvider'

interface Message {
  role: 'user' | 'assistant'
  content: string
  streaming?: boolean
}

const WELCOME: Record<string, string> = {
  es: '¡Hola! Soy **CaddyAI**, tu asistente de golf. Puedo ayudarte con reglas, estrategia, selección de palos y análisis de tu juego. ¿En qué te ayudo?',
  en: "Hi! I'm **CaddyAI**, your golf assistant. I can help with rules, strategy, club selection and game analysis. How can I help?",
}

function renderContent(text: string) {
  // Basic markdown: **bold**, *italic*, bullet lists
  const lines = text.split('\n')
  return lines.map((line, i) => {
    if (line.startsWith('- ') || line.startsWith('• ')) {
      return (
        <li key={i} className="ml-4 list-disc">
          <span dangerouslySetInnerHTML={{ __html: formatInline(line.slice(2)) }} />
        </li>
      )
    }
    if (line.trim() === '') return <br key={i} />
    return (
      <p key={i} className="leading-relaxed"
        dangerouslySetInnerHTML={{ __html: formatInline(line) }} />
    )
  })
}

function formatInline(text: string) {
  return text
    .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
    .replace(/\*(.+?)\*/g, '<em>$1</em>')
    .replace(/`(.+?)`/g, '<code class="bg-zinc-700 px-1 rounded text-xs">$1</code>')
}

export default function ChatWidget() {
  const locale = useLocale()
  const pathname = usePathname()
  const [open, setOpen] = useState(false)
  const [messages, setMessages] = useState<Message[]>([
    { role: 'assistant', content: WELCOME[locale] || WELCOME.es },
  ])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLTextAreaElement>(null)
  const abortRef = useRef<AbortController | null>(null)

  // Extract round_id from path if on a round page
  const roundId = pathname.match(/\/rounds\/([^/]+)/)?.[1] ?? null

  useEffect(() => {
    if (open) {
      messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
      setTimeout(() => inputRef.current?.focus(), 100)
    }
  }, [open, messages])

  const send = useCallback(async () => {
    const text = input.trim()
    if (!text || loading) return

    const token = localStorage.getItem('access_token')
    if (!token) return

    setInput('')
    setLoading(true)

    const userMsg: Message = { role: 'user', content: text }
    const assistantMsg: Message = { role: 'assistant', content: '', streaming: true }

    setMessages((prev) => [...prev, userMsg, assistantMsg])

    // Build history (exclude welcome + current streaming placeholder)
    const history = messages
      .filter((m) => !m.streaming && m.content !== (WELCOME[locale] || WELCOME.es))
      .map((m) => ({ role: m.role, content: m.content }))

    const ctrl = new AbortController()
    abortRef.current = ctrl

    try {
      const res = await fetch('/api/v1/chat', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({ message: text, history, round_id: roundId, locale }),
        signal: ctrl.signal,
      })

      if (!res.ok) throw new Error('Error del servidor')

      const reader = res.body!.getReader()
      const decoder = new TextDecoder()
      let buffer = ''

      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        buffer += decoder.decode(value, { stream: true })
        const lines = buffer.split('\n')
        buffer = lines.pop() || ''

        for (const line of lines) {
          if (!line.startsWith('data: ')) continue
          const raw = line.slice(6).trim()
          if (!raw) continue
          try {
            const parsed = JSON.parse(raw)
            if (parsed.done) break
            if (parsed.error) throw new Error(parsed.error)
            if (parsed.text) {
              setMessages((prev) => {
                const next = [...prev]
                const last = next[next.length - 1]
                if (last.role === 'assistant') {
                  next[next.length - 1] = { ...last, content: last.content + parsed.text }
                }
                return next
              })
            }
          } catch { /* ignore parse errors */ }
        }
      }
    } catch (err: unknown) {
      if ((err as Error).name === 'AbortError') return
      setMessages((prev) => {
        const next = [...prev]
        next[next.length - 1] = {
          role: 'assistant',
          content: locale === 'es'
            ? 'Lo siento, ocurrió un error. Intenta de nuevo.'
            : 'Sorry, an error occurred. Please try again.',
        }
        return next
      })
    } finally {
      setMessages((prev) => {
        const next = [...prev]
        const last = next[next.length - 1]
        if (last.role === 'assistant') {
          next[next.length - 1] = { ...last, streaming: false }
        }
        return next
      })
      setLoading(false)
      abortRef.current = null
    }
  }, [input, loading, messages, roundId, locale])

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      send()
    }
  }

  const clearChat = () => {
    setMessages([{ role: 'assistant', content: WELCOME[locale] || WELCOME.es }])
    abortRef.current?.abort()
  }

  const token = typeof window !== 'undefined' ? localStorage.getItem('access_token') : null
  if (!token) return null

  return (
    <>
      {/* Floating button */}
      <button
        onClick={() => setOpen((v) => !v)}
        className={`fixed bottom-6 right-6 z-50 w-14 h-14 rounded-full shadow-lg flex items-center justify-center transition-all duration-200
          ${open ? 'bg-zinc-700 hover:bg-zinc-600' : 'bg-emerald-500 hover:bg-emerald-400'}`}
        aria-label="CaddyAI"
      >
        {open
          ? <X size={22} className="text-white" />
          : <MessageCircle size={22} className="text-white" />
        }
        {/* Unread dot — only when closed and there are messages */}
        {!open && messages.length > 1 && (
          <span className="absolute top-0 right-0 w-3.5 h-3.5 bg-red-500 rounded-full border-2 border-zinc-950" />
        )}
      </button>

      {/* Chat panel */}
      {open && (
        <div className="fixed bottom-24 right-6 z-50 w-[360px] max-w-[calc(100vw-1.5rem)] h-[520px] max-h-[calc(100dvh-7rem)] flex flex-col bg-zinc-900 border border-zinc-800 rounded-2xl shadow-2xl overflow-hidden">

          {/* Header */}
          <div className="flex items-center gap-3 px-4 py-3 bg-zinc-950 border-b border-zinc-800">
            <div className="w-8 h-8 rounded-full bg-emerald-500 flex items-center justify-center flex-shrink-0">
              <Bot size={16} className="text-white" />
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-sm font-semibold text-white">CaddyAI</p>
              <p className="text-xs text-zinc-500">
                {locale === 'es' ? 'Asistente de golf' : 'Golf assistant'}
              </p>
            </div>
            <button
              onClick={clearChat}
              className="text-zinc-600 hover:text-zinc-400 transition-colors p-1"
              title={locale === 'es' ? 'Limpiar chat' : 'Clear chat'}
            >
              <Trash2 size={15} />
            </button>
          </div>

          {/* Messages */}
          <div className="flex-1 overflow-y-auto p-4 space-y-4 scroll-smooth">
            {messages.map((msg, i) => (
              <div key={i} className={`flex gap-2.5 ${msg.role === 'user' ? 'flex-row-reverse' : ''}`}>
                {/* Avatar */}
                <div className={`w-6 h-6 rounded-full flex-shrink-0 flex items-center justify-center mt-0.5
                  ${msg.role === 'assistant' ? 'bg-emerald-500' : 'bg-zinc-700'}`}>
                  {msg.role === 'assistant'
                    ? <Bot size={13} className="text-white" />
                    : <User size={13} className="text-white" />
                  }
                </div>

                {/* Bubble */}
                <div className={`max-w-[82%] rounded-2xl px-3.5 py-2.5 text-sm
                  ${msg.role === 'assistant'
                    ? 'bg-zinc-800 text-zinc-100 rounded-tl-sm'
                    : 'bg-emerald-600 text-white rounded-tr-sm'
                  }`}>
                  {msg.role === 'assistant' ? (
                    <div className="space-y-1">{renderContent(msg.content)}</div>
                  ) : (
                    <p className="leading-relaxed whitespace-pre-wrap">{msg.content}</p>
                  )}
                  {msg.streaming && (
                    <span className="inline-block w-1.5 h-4 bg-emerald-400 ml-0.5 animate-pulse rounded-sm align-middle" />
                  )}
                </div>
              </div>
            ))}
            <div ref={messagesEndRef} />
          </div>

          {/* Input */}
          <div className="px-3 py-3 bg-zinc-950 border-t border-zinc-800">
            <div className="flex items-end gap-2">
              <textarea
                ref={inputRef}
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder={locale === 'es' ? '¿Qué palo para 150m?' : 'Ask about clubs, rules...'}
                rows={1}
                className="flex-1 bg-zinc-800 border border-zinc-700 rounded-xl px-3.5 py-2.5 text-sm text-white placeholder:text-zinc-600 focus:outline-none focus:border-emerald-500 transition-colors resize-none min-h-[40px] max-h-[120px] overflow-y-auto leading-5"
                style={{ height: 'auto' }}
                onInput={(e) => {
                  const t = e.currentTarget
                  t.style.height = 'auto'
                  t.style.height = Math.min(t.scrollHeight, 120) + 'px'
                }}
                disabled={loading}
              />
              <button
                onClick={send}
                disabled={loading || !input.trim()}
                className="w-10 h-10 flex-shrink-0 bg-emerald-500 hover:bg-emerald-400 disabled:opacity-40 disabled:cursor-not-allowed rounded-xl flex items-center justify-center transition-colors"
              >
                {loading
                  ? <Loader2 size={16} className="text-white animate-spin" />
                  : <Send size={16} className="text-white" />
                }
              </button>
            </div>
            <p className="text-[10px] text-zinc-700 mt-1.5 text-center">
              {locale === 'es' ? 'Enter para enviar · Shift+Enter para nueva línea' : 'Enter to send · Shift+Enter for new line'}
            </p>
          </div>
        </div>
      )}
    </>
  )
}
