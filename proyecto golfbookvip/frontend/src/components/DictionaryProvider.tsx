'use client'
import { createContext, useContext } from 'react'
import type { Locale } from '@/lib/i18n'

type Dict = Record<string, unknown>

interface DictCtx {
  dict: Dict
  locale: Locale
}

const Ctx = createContext<DictCtx>({ dict: {}, locale: 'es' })

export function DictionaryProvider({ dict, locale, children }: { dict: Dict; locale: Locale; children: React.ReactNode }) {
  return <Ctx.Provider value={{ dict, locale }}>{children}</Ctx.Provider>
}

export function useDict() {
  return useContext(Ctx)
}

export function useT(section: string) {
  const { dict } = useContext(Ctx)
  const sec = (dict as Record<string, Record<string, string>>)[section] ?? {}
  return (key: string) => sec[key] ?? key
}

export function useLocale(): Locale {
  return useContext(Ctx).locale
}
