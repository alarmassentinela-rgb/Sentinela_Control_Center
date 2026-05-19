'use client'
import { useState } from 'react'
import Papa from 'papaparse'
import { Upload, FileText, Check, AlertTriangle, X, Loader2, Download, Copy } from 'lucide-react'
import { api } from '@/lib/api'

export interface ParsedRow {
  row_index: number
  email: string
  member_number?: string
  membership_type_name?: string
  membership_type_id?: number
  joined_at?: string
  expires_at?: string
  notes?: string
  status?: 'pending' | 'matched' | 'not_found'
  user_id?: string
  user_name?: string
}

export interface ImportSummary {
  total_rows: number
  created: number
  reactivated: number
  skipped: number
  not_found_count: number
  error_count: number
  details: {
    not_found: { row_index: number; email: string }[]
    errors: { row_index: number; email: string; error: string }[]
  }
  invite_link: string | null
}

interface Props {
  locale: 'es' | 'en'
  // Cuando hay clubId, hace import real contra /clubs/{id}/padron/import.
  // Cuando es null (wizard), solo expone las rows validadas via onRowsReady.
  clubId: string | null
  // Callback con rows parseadas + validadas (wizard usa esto para enviarlas al crear el club)
  onRowsReady?: (rows: ParsedRow[]) => void
  // Callback con resumen tras un import exitoso (modo clubId)
  onImported?: (summary: ImportSummary) => void
}

const HEADER_ALIASES: Record<string, string[]> = {
  email: ['email', 'correo', 'mail', 'e-mail'],
  member_number: ['member_number', 'numero', 'número', 'no_socio', 'num_socio', 'numero_socio', 'número_socio', 'socio'],
  membership_type_name: ['membership_type', 'tipo', 'tipo_membresia', 'tipo de membresía', 'membresia', 'tipo_membresía'],
  joined_at: ['joined_at', 'fecha_ingreso', 'ingreso', 'fecha alta', 'alta'],
  expires_at: ['expires_at', 'vence', 'vencimiento', 'fecha_vencimiento'],
  notes: ['notes', 'notas', 'comentarios', 'observaciones'],
}

function normalizeHeader(h: string): string | null {
  const h_lower = (h || '').trim().toLowerCase()
  for (const [field, aliases] of Object.entries(HEADER_ALIASES)) {
    if (aliases.includes(h_lower)) return field
  }
  return null
}

export default function CsvPadronImport({ locale, clubId, onRowsReady, onImported }: Props) {
  const lbl = (es: string, en: string) => locale === 'es' ? es : en
  const [rows, setRows] = useState<ParsedRow[]>([])
  const [parseError, setParseError] = useState<string | null>(null)
  const [validating, setValidating] = useState(false)
  const [validated, setValidated] = useState(false)
  const [importing, setImporting] = useState(false)
  const [summary, setSummary] = useState<ImportSummary | null>(null)
  const [copied, setCopied] = useState(false)

  const downloadTemplate = () => {
    const headers = 'email,member_number,membership_type,joined_at,expires_at,notes'
    const examples = [
      'juan@ejemplo.com,0001,Socio,2024-01-15,,',
      'maria@ejemplo.com,0002,Honorario,,,Cliente VIP',
    ].join('\n')
    const csv = `${headers}\n${examples}\n`
    const blob = new Blob([csv], { type: 'text/csv;charset=utf-8' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = 'plantilla-padron.csv'
    a.click()
    URL.revokeObjectURL(url)
  }

  const handleFile = (file: File) => {
    setParseError(null)
    setRows([])
    setValidated(false)
    setSummary(null)
    Papa.parse(file, {
      header: true,
      skipEmptyLines: true,
      complete: (res) => {
        if (res.errors && res.errors.length > 0) {
          setParseError(`${lbl('Error al parsear CSV', 'CSV parse error')}: ${res.errors[0].message}`)
          return
        }
        const data = res.data as Record<string, string>[]
        const fields = (res.meta?.fields || []) as string[]
        // Mapear headers crudos a campos conocidos
        const headerMap: Record<string, string> = {}
        for (const h of fields) {
          const norm = normalizeHeader(h)
          if (norm) headerMap[h] = norm
        }
        if (!Object.values(headerMap).includes('email')) {
          setParseError(lbl(
            'El CSV debe tener una columna "email" (o "correo")',
            'CSV must include a column "email"'
          ))
          return
        }
        const parsed: ParsedRow[] = []
        data.forEach((rec, idx) => {
          const row: ParsedRow = { row_index: idx, email: '', status: 'pending' }
          for (const [rawHeader, normField] of Object.entries(headerMap)) {
            const v = (rec[rawHeader] || '').trim()
            if (!v) continue
            if (normField === 'email') row.email = v.toLowerCase()
            else if (normField === 'member_number') row.member_number = v
            else if (normField === 'membership_type_name') row.membership_type_name = v
            else if (normField === 'joined_at') row.joined_at = v
            else if (normField === 'expires_at') row.expires_at = v
            else if (normField === 'notes') row.notes = v
          }
          if (row.email) parsed.push(row)
        })
        if (parsed.length === 0) {
          setParseError(lbl('No se encontraron filas válidas', 'No valid rows found'))
          return
        }
        if (parsed.length > 500) {
          setParseError(lbl(`Máximo 500 filas. Recibidas: ${parsed.length}`, `Max 500 rows. Got: ${parsed.length}`))
          return
        }
        setRows(parsed)
      },
      error: (err) => {
        setParseError(`${lbl('Error', 'Error')}: ${err.message}`)
      },
    })
  }

  const validateEmails = async () => {
    if (rows.length === 0) return
    setValidating(true)
    try {
      const emails = rows.map(r => r.email)
      const res = await api.post('/users/lookup-batch', { emails })
      const matches: Record<string, { user_id: string; first_name: string; last_name: string }> = {}
      for (const m of res.data?.matches || []) {
        matches[m.email] = m
      }
      const updated = rows.map(r => {
        const m = matches[r.email]
        if (m) {
          return { ...r, status: 'matched' as const, user_id: m.user_id, user_name: `${m.first_name || ''} ${m.last_name || ''}`.trim() }
        }
        return { ...r, status: 'not_found' as const }
      })
      setRows(updated)
      setValidated(true)
      onRowsReady?.(updated)
    } catch (e: unknown) {
      const detail = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail
      setParseError(detail || lbl('Error al validar emails', 'Error validating emails'))
    } finally { setValidating(false) }
  }

  const doImport = async () => {
    if (!clubId || rows.length === 0) return
    setImporting(true)
    try {
      const payload = {
        rows: rows.map(r => ({
          email: r.email,
          member_number: r.member_number || null,
          membership_type_name: r.membership_type_name || null,
          joined_at: r.joined_at || null,
          expires_at: r.expires_at || null,
          notes: r.notes || null,
        })),
        skip_existing: true,
      }
      const res = await api.post(`/clubs/${clubId}/padron/import`, payload)
      setSummary(res.data)
      onImported?.(res.data)
    } catch (e: unknown) {
      const detail = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail
      setParseError(detail || lbl('Error al importar', 'Error importing'))
    } finally { setImporting(false) }
  }

  const copyInviteLink = async () => {
    if (!summary?.invite_link) return
    try {
      await navigator.clipboard.writeText(summary.invite_link)
      setCopied(true)
      setTimeout(() => setCopied(false), 1800)
    } catch { /* ignore */ }
  }

  const matchedCount = rows.filter(r => r.status === 'matched').length
  const notFoundCount = rows.filter(r => r.status === 'not_found').length

  // Vista de resultados post-import
  if (summary) {
    return (
      <div className="space-y-3">
        <div className="bg-emerald-500/10 border border-emerald-500/30 rounded-xl p-4 space-y-1">
          <p className="text-sm font-bold text-emerald-300 mb-1">{lbl('Importación completada', 'Import completed')}</p>
          <p className="text-xs text-emerald-200">
            <Check size={11} className="inline" /> {summary.created} {lbl('creados', 'created')}
            {summary.reactivated > 0 && <>{' · '}{summary.reactivated} {lbl('reactivados', 'reactivated')}</>}
            {summary.skipped > 0 && <>{' · '}{summary.skipped} {lbl('ya eran socios', 'already members')}</>}
          </p>
          {summary.error_count > 0 && (
            <p className="text-xs text-red-300"><AlertTriangle size={11} className="inline" /> {summary.error_count} {lbl('con error', 'with errors')}</p>
          )}
        </div>

        {summary.not_found_count > 0 && summary.invite_link && (
          <div className="bg-amber-500/10 border border-amber-500/30 rounded-xl p-4 space-y-2">
            <p className="text-sm font-semibold text-amber-300">
              <AlertTriangle size={12} className="inline mr-1" />
              {summary.not_found_count} {lbl('emails no tienen cuenta en la app', 'emails have no account yet')}
            </p>
            <p className="text-xs text-amber-200/80 leading-relaxed">
              {lbl(
                'Comparte este link de invitación con esos socios para que se registren y queden vinculados automáticamente:',
                'Share this invitation link with those members so they register and link automatically:'
              )}
            </p>
            <div className="flex gap-1">
              <input readOnly value={summary.invite_link}
                onFocus={(e) => e.target.select()}
                className="flex-1 bg-zinc-900 border border-zinc-700 rounded-lg px-2 py-1.5 text-white text-[11px] font-mono" />
              <button onClick={copyInviteLink}
                className="bg-amber-500 hover:bg-amber-400 text-black px-3 rounded-lg text-xs font-semibold flex items-center gap-1.5">
                {copied ? <Check size={12} /> : <Copy size={12} />}
                {copied ? lbl('Copiado', 'Copied') : lbl('Copiar', 'Copy')}
              </button>
            </div>
            <details className="text-[11px] text-amber-200/80 mt-2">
              <summary className="cursor-pointer hover:text-amber-200">{lbl('Ver emails pendientes', 'View pending emails')}</summary>
              <ul className="mt-1 space-y-0.5 pl-3 list-disc">
                {summary.details.not_found.map((nf, i) => (
                  <li key={i}>{nf.email}</li>
                ))}
              </ul>
            </details>
          </div>
        )}

        {summary.error_count > 0 && (
          <details className="bg-red-500/10 border border-red-500/30 rounded-xl p-3 text-xs text-red-200">
            <summary className="cursor-pointer font-semibold">{lbl('Ver errores', 'View errors')}</summary>
            <ul className="mt-2 space-y-0.5 pl-3 list-disc">
              {summary.details.errors.map((e, i) => (
                <li key={i}>{e.email} · {e.error}</li>
              ))}
            </ul>
          </details>
        )}
      </div>
    )
  }

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between gap-2">
        <p className="text-[10px] text-zinc-400 uppercase tracking-wider font-semibold">
          {lbl('Importar padrón desde CSV', 'Import roster from CSV')}
        </p>
        <button onClick={downloadTemplate}
          className="text-[11px] bg-zinc-800 hover:bg-zinc-700 text-zinc-300 px-2 py-1 rounded-lg flex items-center gap-1">
          <Download size={11} /> {lbl('Plantilla', 'Template')}
        </button>
      </div>

      {rows.length === 0 ? (
        <label className="block cursor-pointer">
          <div className="border-2 border-dashed border-zinc-700 hover:border-emerald-500/50 rounded-xl p-8 text-center transition-colors bg-zinc-900/50">
            <Upload size={28} className="text-zinc-500 mx-auto mb-2" />
            <p className="text-sm text-zinc-300 font-semibold">{lbl('Selecciona archivo CSV', 'Choose CSV file')}</p>
            <p className="text-[11px] text-zinc-500 mt-1">
              {lbl('Columnas: email (requerida), member_number, membership_type, joined_at, expires_at, notes', 'Columns: email (required), member_number, membership_type, joined_at, expires_at, notes')}
            </p>
            <input type="file" accept=".csv,text/csv" className="hidden"
              onChange={(e) => { const f = e.target.files?.[0]; if (f) handleFile(f) }} />
          </div>
        </label>
      ) : (
        <div className="space-y-2">
          <div className="flex items-center justify-between bg-zinc-800 rounded-xl px-3 py-2">
            <div className="flex items-center gap-2 text-sm text-zinc-200">
              <FileText size={14} className="text-emerald-400" />
              <span className="font-mono">{rows.length} {lbl('filas', 'rows')}</span>
              {validated && (
                <>
                  <span className="text-emerald-300 flex items-center gap-1 ml-2"><Check size={12} /> {matchedCount}</span>
                  {notFoundCount > 0 && <span className="text-amber-300 flex items-center gap-1"><AlertTriangle size={12} /> {notFoundCount}</span>}
                </>
              )}
            </div>
            <button onClick={() => { setRows([]); setValidated(false); setParseError(null) }}
              className="text-zinc-500 hover:text-red-400"><X size={14} /></button>
          </div>

          <div className="bg-zinc-900 border border-zinc-800 rounded-xl overflow-hidden">
            <div className="max-h-48 overflow-y-auto">
              <table className="w-full text-[11px]">
                <thead className="bg-zinc-800/50 sticky top-0">
                  <tr>
                    <th className="px-2 py-1.5 text-left text-zinc-500 font-semibold">{lbl('Email', 'Email')}</th>
                    <th className="px-2 py-1.5 text-left text-zinc-500 font-semibold">#</th>
                    <th className="px-2 py-1.5 text-left text-zinc-500 font-semibold">{lbl('Tipo', 'Type')}</th>
                    <th className="px-2 py-1.5 text-center text-zinc-500 font-semibold">{lbl('Match', 'Match')}</th>
                  </tr>
                </thead>
                <tbody>
                  {rows.slice(0, 200).map((r, i) => (
                    <tr key={i} className="border-t border-zinc-800/60">
                      <td className="px-2 py-1 text-zinc-300 truncate max-w-[180px]">{r.email}</td>
                      <td className="px-2 py-1 text-zinc-400">{r.member_number || '—'}</td>
                      <td className="px-2 py-1 text-zinc-400">{r.membership_type_name || '—'}</td>
                      <td className="px-2 py-1 text-center">
                        {r.status === 'matched' ? <span title={r.user_name}><Check size={12} className="text-emerald-400 inline" /></span> :
                         r.status === 'not_found' ? <AlertTriangle size={12} className="text-amber-400 inline" /> :
                         <span className="text-zinc-600">—</span>}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
              {rows.length > 200 && (
                <p className="text-[10px] text-zinc-600 text-center py-2">
                  {lbl(`+${rows.length - 200} filas más`, `+${rows.length - 200} more rows`)}
                </p>
              )}
            </div>
          </div>

          <div className="flex gap-2">
            {!validated ? (
              <button onClick={validateEmails} disabled={validating}
                className="flex-1 bg-blue-500 hover:bg-blue-400 disabled:opacity-50 text-white text-sm font-semibold py-2 rounded-xl flex items-center justify-center gap-2">
                {validating ? <Loader2 size={14} className="animate-spin" /> : <Check size={14} />}
                {lbl('Validar emails', 'Validate emails')}
              </button>
            ) : clubId ? (
              <button onClick={doImport} disabled={importing}
                className="flex-1 bg-emerald-500 hover:bg-emerald-400 disabled:opacity-50 text-white text-sm font-semibold py-2 rounded-xl flex items-center justify-center gap-2">
                {importing ? <Loader2 size={14} className="animate-spin" /> : <Upload size={14} />}
                {lbl(`Importar ${matchedCount}`, `Import ${matchedCount}`)}
              </button>
            ) : (
              <div className="flex-1 bg-emerald-500/10 border border-emerald-500/30 rounded-xl px-3 py-2 text-xs text-emerald-300 flex items-center justify-center gap-2">
                <Check size={12} />
                {lbl(`${matchedCount} listos para importar al crear el club`, `${matchedCount} ready to import when club is created`)}
              </div>
            )}
          </div>
        </div>
      )}

      {parseError && (
        <p className="text-xs text-red-300 bg-red-500/10 border border-red-500/30 rounded-lg px-3 py-2">
          {parseError}
        </p>
      )}
    </div>
  )
}
