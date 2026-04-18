import es from '../messages/es.json'
import en from '../messages/en.json'

export type Locale = 'es' | 'en'
export const locales: Locale[] = ['es', 'en']
export const defaultLocale: Locale = 'es'

const dictionaries = { es, en }

export function getDictionary(locale: Locale) {
  return dictionaries[locale] ?? dictionaries[defaultLocale]
}

type NestedValue = string | { [key: string]: NestedValue }

export function t(dict: Record<string, NestedValue>, key: string): string {
  const keys = key.split('.')
  let val: NestedValue = dict
  for (const k of keys) {
    if (typeof val !== 'object') return key
    val = (val as Record<string, NestedValue>)[k]
  }
  return typeof val === 'string' ? val : key
}
